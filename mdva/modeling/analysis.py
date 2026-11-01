"""Análisis del modelo sobre predicciones *out-of-fold* de desarrollo (spec 012, R-46–R-49).

Funciones puras y testeables: importancia por permutación agregada entre folds, dependencia parcial,
segmentación de errores, calibración con *cross-fitting* temporal y curvas de costo de decisión.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.inspection import partial_dependence, permutation_importance
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from mdva.features import LOCAL_TZ
from mdva.modeling import evaluate
from mdva.modeling.calibration import Calibrator

# ── Interpretabilidad ────────────────────────────────────────────────────────


def permutation_importances(
    fitted: list, X: pd.DataFrame, y: np.ndarray, folds, *, n_repeats: int = 5, seed: int = 42, max_rows: int = 20_000
) -> list[dict]:
    """Caída de log loss al permutar cada feature, por fold de validación; media e IC 95 % entre fold×repetición."""
    rng = np.random.default_rng(seed)
    muestras: dict[str, list[float]] = {c: [] for c in X.columns}
    for est, f in zip(fitted, folds, strict=True):
        idx = f.valid if len(f.valid) <= max_rows else rng.choice(f.valid, max_rows, replace=False)
        r = permutation_importance(
            est, X.iloc[idx], y[idx], scoring="neg_log_loss", n_repeats=n_repeats, random_state=seed, n_jobs=1
        )
        for c, vals in zip(X.columns, r.importances, strict=True):
            muestras[c].extend(float(v) for v in vals)
    filas = []
    for c, v in muestras.items():
        v = np.asarray(v)
        filas.append(
            {
                "feature": c,
                "mean": round(float(v.mean()), 5),
                "ci95": [round(float(np.percentile(v, 2.5)), 5), round(float(np.percentile(v, 97.5)), 5)],
            }
        )
    return sorted(filas, key=lambda r: -r["mean"])


def partial_dependences(
    est, X: pd.DataFrame, features: list[str], *, grid_resolution: int = 20, max_rows: int = 5_000, seed: int = 42
) -> dict:
    """PDP (promedio) y una muestra de curvas ICE por feature, en escala de probabilidad."""
    muestra = X.sample(min(max_rows, len(X)), random_state=seed)
    out = {}
    for c in features:
        r = partial_dependence(
            est,
            muestra,
            [c],
            kind="both",
            grid_resolution=grid_resolution,
            percentiles=(0.02, 0.98),
            response_method="predict_proba",
        )
        grid = r["grid_values"][0]
        pdp = r["average"][0]
        ice = r["individual"][0][:30]
        out[c] = {
            "grid": [round(float(g), 4) for g in grid],
            "pdp": [round(float(p), 4) for p in pdp],
            "ice_sample": [[round(float(p), 4) for p in row] for row in ice],
            "trend": _tendencia(grid, pdp),
        }
    return out


def hour_profile(est, X: pd.DataFrame, *, max_rows: int = 5_000, seed: int = 42) -> list[dict]:
    """Dependencia parcial conjunta de (hour_sin, hour_cos): P(lluvia) media al fijar cada hora local.

    La PDP de cada componente por separado no se interpreta (hora = punto en el círculo); fijar ambas a la
    vez da el ciclo diurno que aprendió el modelo, comparable con la climatología del valle.
    """
    muestra = X.sample(min(max_rows, len(X)), random_state=seed).copy()
    filas = []
    for h in range(24):
        muestra["hour_sin"] = np.sin(2 * np.pi * h / 24)
        muestra["hour_cos"] = np.cos(2 * np.pi * h / 24)
        filas.append({"hour_local": h, "mean_probability": round(float(est.predict_proba(muestra)[:, 1].mean()), 4)})
    return filas


def _tendencia(x, y) -> str:
    """Signo de la relación monotónica dominante (Spearman sobre la PDP)."""
    rho = pd.Series(y).corr(pd.Series(x), method="spearman")
    if rho > 0.5:
        return "creciente"
    if rho < -0.5:
        return "decreciente"
    return "no monotónica"


# ── Análisis de errores ──────────────────────────────────────────────────────


def season(month: pd.Series) -> pd.Series:
    """Régimen bimodal del Valle de Aburrá: lluviosas abr–may y sep–nov; secas dic–feb y jun–ago."""
    return month.map(
        lambda m: "lluviosa" if m in (4, 5, 9, 10, 11) else ("seca" if m in (12, 1, 2, 6, 7, 8) else "transición")
    )


def segment_metrics(y: np.ndarray, p: np.ndarray, segments: pd.Series) -> list[dict]:
    filas = []
    for valor, idx in pd.Series(np.arange(len(y))).groupby(segments.to_numpy()).indices.items():
        ys, ps = y[idx], p[idx]
        fila = {
            "segment": str(valor),
            "n": int(len(idx)),
            "rain_rate": round(float(ys.mean()), 4),
            "mean_pred": round(float(ps.mean()), 4),
        }
        if 0 < ys.sum() < len(ys):
            fila |= {
                "roc_auc": round(float(roc_auc_score(ys, ps)), 4),
                "brier": round(float(brier_score_loss(ys, ps)), 4),
                "ece": round(evaluate.expected_calibration_error(ys, ps), 4),
            }
        filas.append(fila)
    return filas


def error_analysis(
    y: np.ndarray, p: np.ndarray, time_utc: pd.Series, cell: pd.Series, precipitation: pd.Series
) -> dict:
    local = time_utc.dt.tz_convert(LOCAL_TZ).reset_index(drop=True)
    bins = pd.cut(
        precipitation.reset_index(drop=True),
        [-0.01, 0.0, 0.1, 0.5, 2.0, np.inf],
        labels=["0", "(0, 0.1]", "(0.1, 0.5]", "(0.5, 2]", ">2"],
    )
    return {
        "hour_local": segment_metrics(y, p, local.dt.hour),
        "season": segment_metrics(y, p, season(local.dt.month)),
        "month": segment_metrics(y, p, local.dt.month),
        "era5_cell": segment_metrics(y, p, cell.reset_index(drop=True).astype(str)),
        "forecast_precip_mm": segment_metrics(y, p, bins.astype(str)),
    }


# ── Calibración con cross-fitting temporal ───────────────────────────────────


def fit_calibrator(method: str, p: np.ndarray, y: np.ndarray) -> Calibrator:
    return Calibrator(method).fit(p, y)


def crossfit_calibration(y: np.ndarray, oof: np.ndarray, folds, methods=("none", "isotonic", "sigmoid")) -> dict:
    """Cada fold k ≥ 2 se calibra con las predicciones OOF de los folds anteriores (nunca con el propio).

    Así se estima honestamente cuánto ayuda calibrar sin tocar el fold evaluado.
    """
    resultados = {m: {"per_fold": []} for m in methods}
    calibradas = {m: np.full(len(y), np.nan) for m in methods}
    for k in range(1, len(folds)):
        previos = np.concatenate([f.valid for f in folds[:k]])
        actual = folds[k].valid
        for m in methods:
            cal = fit_calibrator(m, oof[previos], y[previos])
            q = cal(oof[actual])
            calibradas[m][actual] = q
            resultados[m]["per_fold"].append(
                {
                    "fold": folds[k].name,
                    "log_loss": round(float(log_loss(y[actual], q, labels=[0, 1])), 5),
                    "ece": round(evaluate.expected_calibration_error(y[actual], q), 5),
                }
            )
    evaluados = np.concatenate([f.valid for f in folds[1:]])
    for m in methods:
        q = calibradas[m][evaluados]
        resultados[m]["log_loss"] = round(float(log_loss(y[evaluados], q, labels=[0, 1])), 5)
        resultados[m]["ece"] = round(evaluate.expected_calibration_error(y[evaluados], q), 5)
        resultados[m]["reliability"] = evaluate.reliability(y[evaluados], q)
    elegido = min(methods, key=lambda m: resultados[m]["log_loss"])
    return {"methods": resultados, "chosen": elegido, "evaluated_folds": [f.name for f in folds[1:]]}


# ── Análisis de decisión ─────────────────────────────────────────────────────


def cost_curves(y: np.ndarray, p: np.ndarray, ratios=(1, 2, 3, 4, 5), thresholds=None, business=(0.40, 0.70)) -> dict:
    """Costo esperado por hora de alertar con umbral τ, con costo(falsa alarma)=1 y costo(lluvia no avisada)=r.

    Para probabilidades calibradas el umbral óptimo teórico es 1/(1+r). Se reporta el óptimo empírico,
    el teórico y el costo relativo de los cortes de negocio frente al óptimo.
    """
    thresholds = np.round(np.arange(0.05, 0.96, 0.01), 2) if thresholds is None else np.asarray(thresholds)
    y = np.asarray(y, dtype=int)
    out = {"thresholds": thresholds.tolist(), "ratios": {}}
    for r in ratios:
        costos = []
        for tau in thresholds:
            alerta = p >= tau
            fp = np.sum(alerta & (y == 0))
            fn = np.sum(~alerta & (y == 1))
            costos.append(float((fp + r * fn) / len(y)))
        costos = np.asarray(costos)
        i = int(np.argmin(costos))
        sin_alerta = float(r * y.mean())  # nunca alertar

        def costo_en(tau):
            return float(costos[int(np.argmin(np.abs(thresholds - tau)))])

        out["ratios"][str(r)] = {
            "cost": [round(c, 5) for c in costos],
            "optimal_threshold": float(thresholds[i]),
            "theoretical_threshold": round(1 / (1 + r), 3),
            "optimal_cost": round(float(costos[i]), 5),
            "never_alert_cost": round(sin_alerta, 5),
            "business_thresholds": {
                str(b): {"cost": round(costo_en(b), 5), "regret_vs_optimal": round(costo_en(b) - float(costos[i]), 5)}
                for b in business
            },
        }
    return out
