"""Entrena, calibra y evalúa el clasificador de lluvia (spec 005).

1. Features con `mdva.features` sobre el dataset `rain_hourly` (spec 003).
2. Split temporal: train 2022–2023 (sin junio–julio de 2022), validación 2024, prueba 2025.
3. Selección por log loss en validación entre regresión logística e HistGradientBoosting.
4. Calibración sobre validación (método elegido con un sub-split temporal de la validación).
5. Evaluación única en prueba frente a baselines, con IC por bootstrap en bloques de días,
   curva de confiabilidad, niveles de alerta y validación externa contra pluviómetros SIATA.
6. Artefactos: modelo + metadata + model card, métricas, figuras y registro de corrida.

Uso (desde la raíz del repo, con el dataset construido):
    python -m mdva.modeling.train
"""

from __future__ import annotations

import argparse
import itertools
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
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mdva import config, openmeteo
from mdva.data_contract import DATASET_CONTRACT
from mdva.dataset import content_fingerprint
from mdva.features import FEATURE_CONTRACT_VERSION, FEATURES, build_features
from mdva.label_validation import siata_hourly
from mdva.modeling import evaluate, model_card, splits
from mdva.modeling.baselines import Climatology, RawForecast, persistence
from mdva.modeling.predict import MODEL_NAME, model_dir

log = logging.getLogger(__name__)

MODEL_VERSION = "1.0.0"
SEED = 42
ALERT_THRESHOLDS = {"amarillo": 0.40, "rojo": 0.70}
HGB_GRID = {
    "learning_rate": (0.05, 0.1),
    "max_leaf_nodes": (15, 31),
    "max_iter": (200, 400),
    "l2_regularization": (0.0, 1.0),
}
MAX_MODEL_BYTES = 5_000_000


def candidates():
    yield "logistic", {}, make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    claves = list(HGB_GRID)
    for valores in itertools.product(*HGB_GRID.values()):
        params = dict(zip(claves, valores))
        yield "hgb", params, HistGradientBoostingClassifier(early_stopping=False, random_state=SEED, **params)


def _ll(y, p) -> float:
    return float(log_loss(y, np.clip(p, evaluate.EPS, 1 - evaluate.EPS), labels=[0, 1]))


def choose_calibration(base, X_val: pd.DataFrame, y_val: np.ndarray, t_val: pd.Series) -> tuple[str, dict]:
    """Elige entre sin calibrar, isotónica y sigmoide: ajusta en enero–junio y evalúa en julio–diciembre de 2024."""
    corte = pd.Timestamp("2024-07-01", tz="UTC")
    a, b = (t_val < corte).to_numpy(), (t_val >= corte).to_numpy()
    resultados = {"none": round(_ll(y_val[b], base.predict_proba(X_val[b])[:, 1]), 5)}
    for metodo in ("isotonic", "sigmoid"):
        cal = CalibratedClassifierCV(FrozenEstimator(base), method=metodo).fit(X_val[a], y_val[a])
        resultados[metodo] = round(_ll(y_val[b], cal.predict_proba(X_val[b])[:, 1]), 5)
    return min(resultados, key=resultados.get), resultados


def calibrate(base, metodo: str, X_val: pd.DataFrame, y_val: np.ndarray):
    if metodo == "none":
        return base
    return CalibratedClassifierCV(FrozenEstimator(base), method=metodo).fit(X_val, y_val)


def git_info() -> tuple[str, bool]:
    try:
        sha = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        sucio = bool(subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
        return sha, sucio
    except (OSError, subprocess.CalledProcessError):
        return "desconocido", True


def run(
    dataset: pd.DataFrame | None = None,
    *,
    n_boot: int = 500,
    siata_hours: pd.DataFrame | None = None,
    out_models=None,
    out_reports=None,
) -> dict:
    inicio = time.time()
    df = dataset if dataset is not None else pd.read_parquet(config.DATASET_PROCESSED)
    df = df.sort_values(["time_utc", "station_id"]).reset_index(drop=True)
    X = build_features(df)
    y = df["rain"].to_numpy(dtype=int)
    t = df["time_utc"]
    masks = {k: v.to_numpy() for k, v in splits.temporal_splits(t).items()}
    tr, va, te, ex = masks["train"], masks["validation"], masks["test"], masks["external"]

    # ── Selección ────────────────────────────────────────────────────────────
    seleccion = []
    mejor = None
    for nombre, params, est in candidates():
        est.fit(X[tr], y[tr])
        ll = _ll(y[va], est.predict_proba(X[va])[:, 1])
        seleccion.append({"name": nombre, "params": params, "val_log_loss": round(ll, 5)})
        log.info("candidato %s %s → log loss validación %.5f", nombre, params, ll)
        if mejor is None or ll < mejor[0]:
            mejor = (ll, nombre, params, est)
    _, nombre_base, params_base, base = mejor
    logistica = next(c for c in seleccion if c["name"] == "logistic")
    modelo_logistico = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X[tr], y[tr])

    # ── Calibración ──────────────────────────────────────────────────────────
    metodo, comparacion = choose_calibration(base, X[va], y[va], t[va].reset_index(drop=True))
    modelo = calibrate(base, metodo, X[va], y[va])

    # ── Baselines ────────────────────────────────────────────────────────────
    clima = Climatology().fit(t[tr], y[tr])
    crudo = RawForecast().fit(X[tr], y[tr])

    def predicciones(m):
        return {
            "model": modelo.predict_proba(X[m])[:, 1],
            "climatology": clima.predict_proba(t[m]),
            "raw_forecast": crudo.predict_proba(X[m]),
            "logistic": modelo_logistico.predict_proba(X[m])[:, 1],
            "persistence_reference": persistence(df.loc[m, "station_id"], t[m], y[m]),
        }

    reporte_splits = {}
    for nombre, m in (("validation", va), ("test", te)):
        preds = predicciones(m)
        puntos = {k: evaluate.point_metrics(y[m], p) for k, p in preds.items()}
        for k in puntos:
            puntos[k]["bss"] = 1 - puntos[k]["brier"] / puntos["climatology"]["brier"]
        reporte_splits[nombre] = {"models": {k: {mk: round(v, 4) for mk, v in r.items()} for k, r in puntos.items()}}
        if nombre == "test":
            dias = t[m].dt.floor("D").to_numpy()
            boot = evaluate.day_block_bootstrap(y[m], preds, dias, n_boot=n_boot, seed=SEED)
            for k in puntos:
                reporte_splits[nombre]["models"][k]["ci95"] = boot["ci95"][k]
            reporte_splits[nombre]["paired_vs_model"] = boot["paired_vs_model"]
            p_test = preds["model"]

    pareadas = reporte_splits["test"]["paired_vs_model"]

    def supera(baseline):
        return all(pareadas[baseline][k]["ci95"][1] < 0 for k in ("brier_diff", "log_loss_diff"))

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

    huella = content_fingerprint(df)
    metrics = {
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "dataset_fingerprint": huella,
        "bootstrap": {"B": n_boot, "block": "day_utc", "seed": SEED},
        "selection": {"candidates": seleccion, "chosen": {"name": nombre_base, "params": params_base}},
        "calibration_choice": {**comparacion, "chosen": metodo},
        "splits": reporte_splits,
        "reliability": {"test": evaluate.reliability(y[te], p_test)},
        "alert_levels": {"test": evaluate.alert_levels(y[te], p_test, **ALERT_THRESHOLDS)},
        "external_siata": externa,
        "claims": {
            "beats_climatology": supera("climatology"),
            "beats_raw_forecast": supera("raw_forecast"),
            "beats_logistic": supera("logistic"),
            "ece_below_0_03": reporte_splits["test"]["models"]["model"]["ece"] < 0.03,
        },
    }

    # ── Artefactos ───────────────────────────────────────────────────────────
    carpeta = model_dir(MODEL_VERSION, out_models)
    carpeta.mkdir(parents=True, exist_ok=True)
    joblib.dump(modelo, carpeta / "model.joblib")
    tamano = (carpeta / "model.joblib").stat().st_size
    if tamano >= MAX_MODEL_BYTES:
        raise RuntimeError(f"El modelo pesa {tamano} bytes (≥ 5 MB): publíquelo como asset de release (charter P7)")

    reports = out_reports or config.REPORTS_DIR
    metrics_path = reports / "metrics" / MODEL_NAME / MODEL_VERSION / "metrics.json"
    sha, sucio = git_info()
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
        "splits": splits.describe(t, pd.Series(y), splits.temporal_splits(t)),
        "base_estimator": {"class": type(base).__name__, "params": params_base},
        "calibration": {"method": metodo, "fitted_on": None if metodo == "none" else "validation"},
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
    openmeteo.write_atomic(carpeta / "model_card.md", model_card.render(metadata, metrics).encode("utf-8"))

    try:
        from mdva import plots

        plots.reliability_diagram(metrics["reliability"]["test"], reports / "figures" / f"{MODEL_NAME}_reliability.png")
        plots.pr_curves(y[te], predicciones(te), reports / "figures" / f"{MODEL_NAME}_pr_curves.png")
    except ImportError:  # pragma: no cover - matplotlib es dependencia del proyecto
        log.warning("matplotlib no disponible: se omiten las figuras")

    corrida = {
        "run_at_utc": metadata["created_at_utc"],
        "git_sha": sha,
        "dirty_worktree": sucio,
        "model_version": MODEL_VERSION,
        "dataset_fingerprint": huella,
        "seed": SEED,
        "grid": {k: list(v) for k, v in HGB_GRID.items()},
        "chosen": metrics["selection"]["chosen"],
        "calibration": metodo,
        "val_metrics": reporte_splits["validation"]["models"]["model"],
        "test_metrics": {k: v for k, v in reporte_splits["test"]["models"]["model"].items() if k != "ci95"},
        "logistic_val_log_loss": logistica["val_log_loss"],
        "duration_s": round(time.time() - inicio, 1),
    }
    _write_json(reports / "runs" / f"{metadata['created_at_utc'].replace(':', '')}_{sha[:7]}.json", corrida)
    return {"metadata": metadata, "metrics": metrics, "run": corrida}


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
    m = r["metrics"]["splits"]["test"]["models"]["model"]
    log.info(
        "Modelo %s listo: prueba ROC-AUC %.3f, Brier %.4f, BSS %.3f, ECE %.4f; afirmaciones %s",
        MODEL_VERSION,
        m["roc_auc"],
        m["brier"],
        m["bss"],
        m["ece"],
        r["metrics"]["claims"],
    )


if __name__ == "__main__":
    main()
