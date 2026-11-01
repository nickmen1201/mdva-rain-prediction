"""Estudio de modelado del clasificador de lluvia (spec 012, charter R-45–R-49).

Todo se decide con validación cruzada temporal *rolling origin* dentro de desarrollo (2022–2024):

1. Features candidatas (ventana del pronóstico, ubicación) con la configuración de referencia 1.0.0;
   la ubicación también con validación espacial (dejar una celda ERA5 fuera).
2. Búsqueda de hiperparámetros (60 HGB + familias de referencia) sobre el conjunto de features elegido;
   regla de un error estándar.
3. Ablación por grupos y curva de aprendizaje con la configuración elegida.
4. Interpretabilidad (permutación con IC, PDP/ICE), análisis de errores *out-of-fold*.
5. Calibración con *cross-fitting* temporal y curvas de costo de decisión.

Salida: `reports/metrics/rain_classifier/study/study.json` (+ figuras). 2025 y 2026 no se leen.

Uso:
    python -m mdva.modeling.study [--quick]
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.base import clone

from mdva import config, openmeteo
from mdva.dataset import content_fingerprint
from mdva.features import (
    BASE_FEATURES,
    FEATURES,
    LOCAL_TZ,
    LOCATION_FEATURES,
    WINDOW_FEATURES,
    build_features,
    forecast_window_inputs,
)
from mdva.modeling import analysis, cv, search

log = logging.getLogger(__name__)

STUDY_DIR = config.METRICS_DIR / "rain_classifier" / "study"

# Grupos de features del contrato 1.0.0 para la ablación (R-47)
GROUPS = {
    "termodinámica": ["temperature_2m", "relative_humidity_2m", "dew_point_depression"],
    "nubosidad": ["cloud_cover"],
    "viento": ["wind_u", "wind_v"],
    "presión": ["pressure_msl"],
    "precipitación pronosticada": ["precipitation_log1p"],
    "inestabilidad (CAPE)": ["cape_log1p"],
    "hora del día": ["hour_sin", "hour_cos"],
    "estacionalidad": ["month_sin", "month_cos"],
}
LEARNING_MONTHS = (3, 6, 12, 18)
TOP_PDP = 4


def load_development(
    dataset: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, pd.Series, dict]:
    """Dataset de desarrollo con las 24 features del contrato 1.1.0; los candidatos son subconjuntos de columnas."""
    df = dataset if dataset is not None else pd.read_parquet(config.DATASET_PROCESSED)
    df = df.sort_values(["time_utc", "station_id"]).reset_index(drop=True)
    huella = content_fingerprint(df)
    ventana = forecast_window_inputs(df)  # antes de recortar: los vecinos del borde existen en 2025
    # Filas de desarrollo con la ventana completa (solo faltan vecinos en bordes y huecos de la serie;
    # en producción la serie horaria del pronóstico siempre los trae). Mismo conjunto para todos los candidatos.
    dev = cv.development_mask(df["time_utc"]) & ventana.notna().all(axis=1).to_numpy()
    df = pd.concat([df, ventana], axis=1)[dev].reset_index(drop=True)
    X = build_features(df)
    extra = {"window": X[list(WINDOW_FEATURES)], "location": X[list(LOCATION_FEATURES)]}
    return df, X[list(BASE_FEATURES)], df["rain"].to_numpy(dtype=int), df["time_utc"], {"fingerprint": huella, **extra}


def _delta(a: cv.CVResult, b: cv.CVResult) -> dict:
    """b − a por fold (negativo = b mejor), con media, EE y si supera 1 EE."""
    d = np.array([fb["log_loss"] - fa["log_loss"] for fa, fb in zip(a.per_fold, b.per_fold, strict=True)])
    se = float(d.std(ddof=1) / np.sqrt(len(d)))
    return {
        "mean": round(float(d.mean()), 5),
        "se": round(se, 5),
        "per_fold": [round(float(x), 5) for x in d],
        "better_by_1se": bool(d.mean() + se < 0),
    }


def spatial_cv(est, X: pd.DataFrame, y: np.ndarray, t: pd.Series, cell: pd.Series) -> dict:
    """Entrena en las demás celdas hasta 2023 y evalúa en la celda excluida en 2024."""
    corte = pd.Timestamp("2024-01-01", tz="UTC")
    tr_t, va_t = (t < corte - pd.Timedelta(hours=24)).to_numpy(), (t >= corte).to_numpy()
    filas = []
    for c in sorted(cell.unique()):
        en_c = (cell == c).to_numpy()
        tr, va = np.flatnonzero(tr_t & ~en_c), np.flatnonzero(va_t & en_c)
        m = clone(est).fit(X.iloc[tr], y[tr])
        filas.append(
            {"held_out_cell": c, "n_valid": int(len(va)), **cv.fold_metrics(y[va], m.predict_proba(X.iloc[va])[:, 1])}
        )
    return {"per_cell": filas, "mean_log_loss": round(float(np.mean([f["log_loss"] for f in filas])), 5)}


def learning_curve(est, X, y, t, folds) -> list[dict]:
    filas = []
    for meses in (*LEARNING_MONTHS, None):
        lls = []
        for f in folds[-3:]:  # los tres folds más recientes tienen ≥ 18 meses de historia
            tr = f.train
            if meses is not None:
                inicio = t.iloc[f.valid].min() - pd.DateOffset(months=meses)
                tr = tr[(t.iloc[tr] >= inicio).to_numpy()]
            m = clone(est).fit(X.iloc[tr], y[tr])
            lls.append(cv.fold_metrics(y[f.valid], m.predict_proba(X.iloc[f.valid])[:, 1])["log_loss"])
        filas.append(
            {
                "train_months": meses or "todo",
                "mean_log_loss": round(float(np.mean(lls)), 5),
                "per_fold": [round(v, 5) for v in lls],
            }
        )
    return filas


def run(dataset: pd.DataFrame | None = None, *, n_hgb: int = search.N_HGB_TRIALS, quick: bool = False) -> dict:
    inicio = time.time()
    df, X_base, y, t, extra = load_development(dataset)
    folds = cv.rolling_folds(t)
    ref = search.make_hgb(search.V1_PARAMS)
    decisiones = []

    # 1. Features candidatas con la configuración de referencia ──────────────────────────────────
    log.info("1/5 features candidatas")
    w, loc = extra["window"], extra["location"]
    conjuntos = {
        "base": X_base,
        "base+window": pd.concat([X_base, w], axis=1),
        "base+location": pd.concat([X_base, loc], axis=1),
        "base+window+location": pd.concat([X_base, w, loc], axis=1),
    }
    cv_conj = {k: cv.cross_validate(ref, v, y, folds) for k, v in conjuntos.items()}
    candidatas = {k: {"cv": r.summary(), "vs_base": _delta(cv_conj["base"], r)} for k, r in cv_conj.items()}
    # Aporte marginal de cada grupo sobre el conjunto sin él (temporal) y generalización espacial de la ubicación
    marginal = {
        "window|base": _delta(cv_conj["base"], cv_conj["base+window"]),
        "window|location": _delta(cv_conj["base+location"], cv_conj["base+window+location"]),
        "location|base": _delta(cv_conj["base"], cv_conj["base+location"]),
        "location|window": _delta(cv_conj["base+window"], cv_conj["base+window+location"]),
    }
    espacial = {k: spatial_cv(ref, conjuntos[k], y, t, df["era5_cell"]) for k in conjuntos}
    usa_ventana = marginal["window|base"]["better_by_1se"]
    sin_loc = "base+window" if usa_ventana else "base"
    con_loc = "base+window+location" if usa_ventana else "base+location"
    usa_ubicacion = (
        marginal["location|window" if usa_ventana else "location|base"]["better_by_1se"]
        and espacial[con_loc]["mean_log_loss"] < espacial[sin_loc]["mean_log_loss"]
    )
    elegido_conj = con_loc if usa_ubicacion else sin_loc
    X = conjuntos[elegido_conj]
    decisiones.append(
        {
            "decision": f"ventana del pronóstico {'adoptada' if usa_ventana else 'descartada'}",
            "evidence": "study.json:feature_candidates.marginal",
            "data": "CV temporal desarrollo 2022–2024",
        }
    )
    decisiones.append(
        {
            "decision": f"ubicación (lat/lon) {'adoptada' if usa_ubicacion else 'descartada'}",
            "evidence": "study.json:feature_candidates.marginal, spatial_cv",
            "data": "CV temporal y espacial (dejar una celda ERA5 fuera), desarrollo",
        }
    )

    # 2. Búsqueda de hiperparámetros ──────────────────────────────────────────────────────────────
    log.info("2/5 búsqueda de hiperparámetros sobre %s", elegido_conj)
    s = search.search(X, y, folds, n_hgb=2 if quick else n_hgb, quick=quick)
    elegido = s["chosen"]
    final = search.FAMILIES[elegido.family](elegido.params)
    decisiones.append(
        {
            "decision": f"{elegido.family} {elegido.params} (regla de 1 EE)",
            "evidence": "study.json:search",
            "data": "CV desarrollo 2022–2024",
        }
    )

    # 3. Ablación y curva de aprendizaje ──────────────────────────────────────────────────────────
    log.info("3/5 ablación y curva de aprendizaje")
    ablacion = {}
    grupos = dict(GROUPS)
    if usa_ventana:
        grupos["ventana del pronóstico"] = list(w.columns)
    if usa_ubicacion:
        grupos["ubicación"] = list(loc.columns)
    for grupo, cols in grupos.items():
        r = cv.cross_validate(final, X.drop(columns=cols), y, folds)
        ablacion[grupo] = {"removed": cols, "cv": r.summary(), "delta_vs_full": _delta(elegido.cv, r)}
    curva = learning_curve(final, X, y, t, folds)

    # 4. Interpretabilidad y errores ──────────────────────────────────────────────────────────────
    log.info("4/5 interpretabilidad y análisis de errores")
    ajustados = [clone(final).fit(X.iloc[f.train], y[f.train]) for f in folds]
    importancias = analysis.permutation_importances(ajustados, X, y, folds, n_repeats=2 if quick else 5)
    # PDP de las principales features continuas; la hora (sin/cos) se resume con su perfil conjunto
    top = [r["feature"] for r in importancias if not r["feature"].startswith("hour_")][:TOP_PDP]
    pdp = analysis.partial_dependences(ajustados[-1], X.iloc[folds[-1].valid], top)
    perfil_horario = analysis.hour_profile(ajustados[-1], X.iloc[folds[-1].valid])
    tasa_por_hora = [
        {"hour_local": int(h), "rain_rate": round(float(v), 4)}
        for h, v in pd.Series(y[folds[-1].valid])
        .groupby(t.iloc[folds[-1].valid].dt.tz_convert(LOCAL_TZ).dt.hour.to_numpy())
        .mean()
        .items()
    ]
    oof, validos = elegido.cv.oof, np.concatenate([f.valid for f in folds])
    errores = analysis.error_analysis(
        y[validos], oof[validos], t.iloc[validos], df["era5_cell"].iloc[validos], df["precipitation"].iloc[validos]
    )

    # 5. Calibración y decisión ───────────────────────────────────────────────────────────────────
    log.info("5/5 calibración y curvas de costo")
    calibracion = analysis.crossfit_calibration(y, oof, folds)
    metodo = calibracion["chosen"]
    evaluados = np.concatenate([f.valid for f in folds[1:]])
    cal_map = analysis.fit_calibrator(metodo, oof[validos], y[validos])
    q = np.clip(cal_map(oof[evaluados]), 1e-6, 1 - 1e-6)
    costos = analysis.cost_curves(y[evaluados], q)
    decisiones.append(
        {
            "decision": f"calibración = {metodo}",
            "evidence": "study.json:calibration",
            "data": "cross-fitting temporal sobre OOF de desarrollo",
        }
    )
    decisiones.append(
        {
            "decision": "umbrales 0.40/0.70 (RF-10) contrastados con el umbral de costo mínimo",
            "evidence": "study.json:decision",
            "data": "OOF calibrado de desarrollo (folds 2–6)",
        }
    )

    resultado = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset_fingerprint": extra["fingerprint"],
        "development": {
            "start": t.min().isoformat(),
            "end": t.max().isoformat(),
            "rows": int(len(t)),
            "rain_rate": round(float(y.mean()), 4),
        },
        "folds": [
            {
                "name": f.name,
                "train_rows": int(len(f.train)),
                "valid_rows": int(len(f.valid)),
                "valid_start": t.iloc[f.valid].min().isoformat(),
                "valid_end": t.iloc[f.valid].max().isoformat(),
            }
            for f in folds
        ],
        "feature_candidates": {"sets": candidatas, "marginal": marginal},
        "spatial_cv": espacial,
        "feature_set": {"name": elegido_conj, "features": list(X.columns), "contract_1_1_0": list(FEATURES)},
        "search": {
            "space": {k: list(v) if isinstance(v, tuple) else v for k, v in search.HGB_SPACE.items()},
            "n_hgb_trials": 2 if quick else n_hgb,
            "trials": [tr.row() for tr in s["trials"]],
            "best": s["best"].row(),
            "chosen": s["chosen"].row(),
            "v1_reference": s["v1"].row(),
            "chosen_vs_v1": _delta(s["v1"].cv, elegido.cv),
            "best_by_family": {
                fam: min((tr for tr in s["trials"] if tr.family == fam), key=lambda tr: tr.cv.mean["log_loss"]).row()
                for fam in ("hgb", "spline_logistic", "random_forest")
            },
        },
        "ablation": ablacion,
        "learning_curve": curva,
        "permutation_importance": importancias,
        "partial_dependence": pdp,
        "hour_profile": {"model": perfil_horario, "observed_rate_last_fold": tasa_por_hora},
        "errors_oof": errores,
        "calibration": calibracion,
        "decision": costos,
        "decision_log": decisiones,
        "duration_s": round(time.time() - inicio, 1),
    }
    resultado["_chosen_estimator"] = final  # no se serializa: lo usa train.py en la misma corrida si hace falta
    return resultado


def write(resultado: dict, out_dir=STUDY_DIR, figures_dir=None) -> None:
    datos = {k: v for k, v in resultado.items() if not k.startswith("_")}
    out_dir.mkdir(parents=True, exist_ok=True)
    openmeteo.write_atomic(
        out_dir / "study.json", json.dumps(datos, indent=2, ensure_ascii=False, default=_json).encode("utf-8") + b"\n"
    )
    try:
        from mdva import plots

        plots.study_figures(datos, figures_dir or config.FIGURES_DIR)
    except ImportError:  # pragma: no cover
        log.warning("matplotlib no disponible: se omiten las figuras")


def _json(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--quick", action="store_true", help="corrida corta para verificar el pipeline")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    r = run(quick=args.quick)
    write(r)
    log.info("Estudio listo en %.0f s: %s", r["duration_s"], r["decision_log"])


if __name__ == "__main__":
    main()
