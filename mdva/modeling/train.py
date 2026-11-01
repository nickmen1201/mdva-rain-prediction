"""Entrena el clasificador de lluvia 1.1.0 a partir del estudio y lo evalúa una sola vez (specs 005 y 012).

1. Lee las decisiones de `study.json` (spec 012): familia e hiperparámetros (regla de 1 EE), features
   (contrato 1.1.0) y método de calibración, todas tomadas con CV temporal dentro de 2022–2024.
2. Entrena en todo el periodo de desarrollo; el mapa de calibración se ajusta sobre predicciones
   *out-of-fold* de los mismos folds del estudio (cross-fitting), nunca sobre lo que vio el modelo.
3. Evalúa **una vez** en 2025 (prueba, ya usada para reportar la versión 1.0.0) y en el holdout fresco
   2026 (nunca usado), frente a climatología, pronóstico crudo, regresión logística y el modelo 1.0.0,
   con IC por bootstrap en bloques de días y diferencias pareadas.
4. Validación externa contra pluviómetros SIATA (jun–jul 2022, fuera del entrenamiento).
5. Artefactos: modelo + metadata + model card, métricas, figuras, registro de corrida y de decisiones.

Uso (desde la raíz del repo, con `make data`, `make data-holdout` y `make study` hechos):
    python -m mdva.modeling.train
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import subprocess
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mdva import config, openmeteo
from mdva.data_contract import DATASET_CONTRACT
from mdva.dataset import content_fingerprint
from mdva.features import BASE_FEATURES, FEATURE_CONTRACT_VERSION, FEATURES, build_features, forecast_window_inputs
from mdva.label_validation import siata_hourly
from mdva.modeling import cv, evaluate, model_card, search, splits
from mdva.modeling.baselines import Climatology, RawForecast, persistence
from mdva.modeling.calibration import CalibratedModel, Calibrator
from mdva.modeling.predict import MODEL_NAME, model_dir
from mdva.modeling.study import STUDY_DIR

log = logging.getLogger(__name__)

MODEL_VERSION = "1.1.0"
PREVIOUS_VERSION = "1.0.0"
SEED = 42
ALERT_THRESHOLDS = {"amarillo": 0.40, "rojo": 0.70}
MAX_MODEL_BYTES = 5_000_000
HOLDOUT = (
    pd.Timestamp(f"{config.HOLDOUT_YEAR}-01-01", tz="UTC") + splits.GAP,
    pd.Timestamp(config.HOLDOUT_END, tz="UTC") + pd.Timedelta(days=1),
)


def git_info() -> tuple[str, bool]:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        sucio = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
        return sha, sucio
    except (OSError, subprocess.CalledProcessError):
        return "desconocido", True


def load_frames(
    dataset: pd.DataFrame | None = None, holdout: pd.DataFrame | None = None
) -> tuple[pd.DataFrame, str, str | None]:
    """Dataset principal + holdout con las entradas de la ventana (sin filas con ventana incompleta) y sus huellas."""
    principal = dataset if dataset is not None else pd.read_parquet(config.DATASET_PROCESSED)
    partes = [principal.assign(_holdout=False)]
    fresco = (
        holdout
        if holdout is not None
        else (pd.read_parquet(config.HOLDOUT_PROCESSED) if config.HOLDOUT_PROCESSED.exists() else None)
    )
    huellas = (content_fingerprint(principal), content_fingerprint(fresco) if fresco is not None else None)
    if fresco is not None:
        partes.append(fresco.assign(_holdout=True))
    df = pd.concat(partes, ignore_index=True).sort_values(["time_utc", "station_id"]).reset_index(drop=True)
    ventana = forecast_window_inputs(df)  # la serie continua 2025 → 2026 da los vecinos del borde
    completas = ventana.notna().all(axis=1)
    log.info("Filas sin ventana completa descartadas: %d", int((~completas).sum()))
    return pd.concat([df, ventana], axis=1)[completas].reset_index(drop=True), *huellas


def read_study(path=STUDY_DIR / "study.json") -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Falta {path}: ejecute `make study` antes de `make train`")
    return json.loads(path.read_text(encoding="utf-8"))


def run(
    dataset: pd.DataFrame | None = None,
    holdout: pd.DataFrame | None = None,
    *,
    study: dict | None = None,
    n_boot: int = 500,
    siata_hours: pd.DataFrame | None = None,
    out_models=None,
    out_reports=None,
    compare_previous: bool = True,
) -> dict:
    inicio = time.time()
    estudio = study if study is not None else read_study()
    if estudio["feature_set"]["features"] != list(FEATURES):
        raise RuntimeError("El estudio eligió features distintas del contrato implementado en mdva/features.py")

    df, huella, huella_holdout = load_frames(dataset, holdout)
    t = df["time_utc"]
    X = build_features(df)
    y = df["rain"].to_numpy(dtype=int)
    es_holdout = df["_holdout"].to_numpy()
    principal = splits.temporal_splits(t)
    dev = cv.development_mask(t) & ~es_holdout
    te = principal["test"].to_numpy() & ~es_holdout
    ho = ((t >= HOLDOUT[0]) & (t < HOLDOUT[1])).to_numpy() & es_holdout
    ex = principal["external"].to_numpy() & ~es_holdout

    # ── Modelo elegido por el estudio ────────────────────────────────────────
    elegido = estudio["search"]["chosen"]
    familia, params = elegido["family"], elegido["params"]
    base_est = search.FAMILIES[familia](params)
    dev_idx = np.flatnonzero(dev)
    t_dev = t.iloc[dev_idx].reset_index(drop=True)
    folds = cv.rolling_folds(t_dev)
    X_dev, y_dev = X.iloc[dev_idx].reset_index(drop=True), y[dev_idx]

    # Mapa de calibración sobre OOF (cross-fitting, mismos folds del estudio)
    metodo = estudio["calibration"]["chosen"]
    oof = cv.cross_validate(base_est, X_dev, y_dev, folds).oof
    validos = np.concatenate([f.valid for f in folds])
    calibrador = Calibrator(metodo).fit(oof[validos], y_dev[validos])
    base = clone(base_est).fit(X_dev, y_dev)
    modelo = CalibratedModel(base, calibrador)
    log.info("Modelo %s %s entrenado en %d filas; calibración %s", familia, params, len(dev_idx), metodo)

    # ── Baselines (todos ajustados en desarrollo) ────────────────────────────
    clima = Climatology().fit(t.iloc[dev_idx], y_dev)
    crudo = RawForecast().fit(X_dev, y_dev)
    logistica = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X_dev, y_dev)
    anterior = _load_previous() if compare_previous else None

    def predicciones(m: np.ndarray) -> dict:
        Xm = X[m]
        p = {
            "model": modelo.predict_proba(Xm)[:, 1],
            "climatology": clima.predict_proba(t[m]),
            "raw_forecast": crudo.predict_proba(Xm),
            "logistic": logistica.predict_proba(Xm)[:, 1],
            "persistence_reference": persistence(df.loc[m, "station_id"], t[m], y[m]),
        }
        if anterior is not None:
            p["model_1_0_0"] = anterior.predict_proba(Xm[list(BASE_FEATURES)])[:, 1]
        return p

    reporte = {}
    for nombre, m in (("test_2025", te), ("holdout_2026", ho)):
        if not m.any():
            log.warning("Sin filas para %s: se omite", nombre)
            continue
        preds = predicciones(m)
        puntos = {k: evaluate.point_metrics(y[m], p) for k, p in preds.items()}
        for k in puntos:
            puntos[k]["bss"] = 1 - puntos[k]["brier"] / puntos["climatology"]["brier"]
        dias = t[m].dt.floor("D").to_numpy()
        boot = evaluate.day_block_bootstrap(y[m], preds, dias, n_boot=n_boot, seed=SEED)
        reporte[nombre] = {
            "period": [t[m].min().isoformat(), t[m].max().isoformat()],
            "rows": int(m.sum()),
            "rain_rate": round(float(y[m].mean()), 4),
            "models": {
                k: {mk: round(v, 4) for mk, v in r.items()} | {"ci95": boot["ci95"][k]} for k, r in puntos.items()
            },
            "paired_vs_model": boot["paired_vs_model"],
            "reliability": evaluate.reliability(y[m], preds["model"]),
            "alert_levels": evaluate.alert_levels(y[m], preds["model"], **ALERT_THRESHOLDS),
        }
        reporte[nombre]["claims"] = {
            f"beats_{b}": all(boot["paired_vs_model"][b][k]["ci95"][1] < 0 for k in ("brier_diff", "log_loss_diff"))
            for b in boot["paired_vs_model"]
        } | {"ece_below_0_03": puntos["model"]["ece"] < 0.03}
        if nombre == "test_2025":
            y_test, preds_test = y[m], preds

    # ── Validación externa contra SIATA ──────────────────────────────────────
    horas = siata_hours if siata_hours is not None else siata_hourly()[0]
    ext = df.loc[ex, ["station_id", "time_utc", "precipitation", "precipitation_ref"]].assign(
        p_model=modelo.predict_proba(X[ex])[:, 1]
    )
    ext = ext.merge(horas[["station_id", "time_utc", "rain_obs"]], on=["station_id", "time_utc"], how="inner")
    externa = evaluate.external_validation(
        ext["rain_obs"].to_numpy(),
        ext["p_model"].to_numpy(),
        ext["precipitation"].to_numpy(),
        ext["precipitation_ref"].to_numpy(),
        ALERT_THRESHOLDS["amarillo"],
    )

    decisiones = estudio["decision_log"] + [
        {
            "decision": f"modelo final {familia} entrenado en todo desarrollo con calibración {metodo} (mapa OOF)",
            "evidence": "metadata.json",
            "data": "desarrollo 2022–2024",
        },
        {
            "decision": "evaluación única en 2025 y en el holdout fresco 2026 (ninguna decisión usa estos periodos)",
            "evidence": "metrics.json:splits",
            "data": "2025 (ya visto por 1.0.0) y 2026-01 → " + config.HOLDOUT_END,
        },
    ]
    metrics = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "dataset_fingerprint": huella,
        "holdout_fingerprint": huella_holdout,
        "bootstrap": {"B": n_boot, "block": "day_utc", "seed": SEED},
        "study": {
            "path": "reports/metrics/rain_classifier/study/study.json",
            "chosen": elegido,
            "chosen_vs_v1_cv": estudio["search"]["chosen_vs_v1"],
            "calibration_crossfit": {
                m: {"log_loss": d["log_loss"], "ece": d["ece"]} for m, d in estudio["calibration"]["methods"].items()
            },
        },
        "splits": reporte,
        "external_siata": externa,
        "decision_log": decisiones,
    }

    # ── Artefactos ───────────────────────────────────────────────────────────
    carpeta = model_dir(MODEL_VERSION, out_models)
    carpeta.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, carpeta / "model.joblib", compress=3)
    tamano = (carpeta / "model.joblib").stat().st_size
    if tamano >= MAX_MODEL_BYTES:
        raise RuntimeError(f"El modelo pesa {tamano} bytes (≥ 5 MB): publíquelo como asset de release (charter P7)")

    reports = out_reports or config.REPORTS_DIR
    metrics_path = reports / "metrics" / MODEL_NAME / MODEL_VERSION / "metrics.json"
    sha, sucio = git_info()
    t_principal = t[~es_holdout].reset_index(drop=True)
    descripcion = splits.describe(
        t_principal,
        pd.Series(y[~es_holdout]),
        {k: v.to_numpy() for k, v in splits.temporal_splits(t_principal).items()},
    )
    descripcion["development"] = {
        "start": t[dev].min().isoformat(),
        "end": t[dev].max().isoformat(),
        "rows": int(dev.sum()),
        "rain_rate": round(float(y[dev].mean()), 4),
    }
    if ho.any():
        descripcion["holdout_2026"] = {
            "start": t[ho].min().isoformat(),
            "end": t[ho].max().isoformat(),
            "rows": int(ho.sum()),
            "rain_rate": round(float(y[ho].mean()), 4),
        }
    metadata = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": sha,
        "dataset_contract_version": DATASET_CONTRACT.version,
        "dataset_fingerprint": huella,
        "feature_contract_version": FEATURE_CONTRACT_VERSION,
        "features": list(FEATURES),
        "label": {"threshold_mm": config.LABEL_THRESHOLD_MM, "source": "ERA5"},
        "splits": descripcion,
        "base_estimator": {"class": type(base).__name__, "family": familia, "params": params},
        "calibration": {"method": metodo, "fitted_on": "predicciones out-of-fold de desarrollo (cross-fitting)"},
        "alert_thresholds": ALERT_THRESHOLDS,
        "seed": SEED,
        "library_versions": {
            "python": platform.python_version(),
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "size_bytes": tamano,
        "metrics_path": metrics_path.relative_to(config.PROJ_ROOT).as_posix()
        if metrics_path.is_relative_to(config.PROJ_ROOT)
        else metrics_path.as_posix(),
    }
    _write_json(carpeta / "metadata.json", metadata)
    _write_json(metrics_path, metrics)
    openmeteo.write_atomic(carpeta / "model_card.md", model_card.render(metadata, metrics, estudio).encode("utf-8"))

    try:
        from mdva import plots

        if "test_2025" in reporte:
            plots.reliability_diagram(
                reporte["test_2025"]["reliability"],
                reports / "figures" / f"{MODEL_NAME}_reliability.png",
                extra={"holdout 2026": reporte.get("holdout_2026", {}).get("reliability")},
            )
            plots.pr_curves(y_test, preds_test, reports / "figures" / f"{MODEL_NAME}_pr_curves.png")
    except ImportError:  # pragma: no cover - matplotlib es dependencia del pipeline
        log.warning("matplotlib no disponible: se omiten las figuras")

    corrida = {
        "run_at_utc": metadata["created_at_utc"],
        "git_sha": sha,
        "dirty_worktree": sucio,
        "model_version": MODEL_VERSION,
        "dataset_fingerprint": huella,
        "holdout_fingerprint": huella_holdout,
        "seed": SEED,
        "chosen": elegido["params"] | {"family": familia},
        "calibration": metodo,
        "test_2025": {
            k: v for k, v in reporte.get("test_2025", {}).get("models", {}).get("model", {}).items() if k != "ci95"
        },
        "holdout_2026": {
            k: v for k, v in reporte.get("holdout_2026", {}).get("models", {}).get("model", {}).items() if k != "ci95"
        },
        "duration_s": round(time.time() - inicio, 1),
    }
    _write_json(reports / "runs" / f"{metadata['created_at_utc'].replace(':', '')}_{sha[:7]}.json", corrida)
    return {"metadata": metadata, "metrics": metrics, "run": corrida}


def _load_previous():
    """Modelo 1.0.0 (13 features) para la comparación pareada; None si no está."""
    ruta = model_dir(PREVIOUS_VERSION) / "model.joblib"
    if not ruta.exists():
        return None
    return joblib.load(ruta)


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    openmeteo.write_atomic(path, json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--n-boot", type=int, default=500)
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    r = run(n_boot=args.n_boot)
    for nombre, s in r["metrics"]["splits"].items():
        m = s["models"]["model"]
        log.info(
            "%s: ROC-AUC %.3f, Brier %.4f, BSS %.3f, ECE %.4f; %s",
            nombre,
            m["roc_auc"],
            m["brier"],
            m["bss"],
            m["ece"],
            s["claims"],
        )


if __name__ == "__main__":
    main()
