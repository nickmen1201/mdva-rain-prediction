"""Métricas, incertidumbre y validación externa (spec 005, research R5–R7)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    cohen_kappa_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

EPS = 1e-6
METRICS = ("roc_auc", "pr_auc", "brier", "log_loss", "ece")


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    idx = np.minimum((p * bins).astype(int), bins - 1)
    total = 0.0
    for b in range(bins):
        m = idx == b
        if m.any():
            total += m.mean() * abs(p[m].mean() - y[m].mean())
    return float(total)


def point_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return {
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "ece": expected_calibration_error(y, p),
    }


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    idx = np.minimum((np.asarray(p) * bins).astype(int), bins - 1)
    filas = []
    for b in range(bins):
        m = idx == b
        if m.any():
            filas.append(
                {
                    "bin": f"[{b / bins:.1f}, {(b + 1) / bins:.1f})",
                    "mean_pred": round(float(p[m].mean()), 4),
                    "obs_rate": round(float(y[m].mean()), 4),
                    "n": int(m.sum()),
                }
            )
    return filas


def day_block_bootstrap(
    y: np.ndarray,
    preds: dict[str, np.ndarray],
    days: np.ndarray,
    *,
    reference: str = "climatology",
    model: str = "model",
    n_boot: int = 500,
    seed: int = 42,
) -> dict:
    """IC 95 % remuestreando días completos; incluye diferencias pareadas modelo − baseline."""
    y = np.asarray(y, dtype=int)
    grupos = pd.Series(np.arange(len(y))).groupby(np.asarray(days)).indices
    bloques = list(grupos.values())
    rng = np.random.default_rng(seed)
    muestras: dict[str, dict[str, list[float]]] = {n: {k: [] for k in (*METRICS, "bss")} for n in preds}
    diffs: dict[str, dict[str, list[float]]] = {n: {"brier_diff": [], "log_loss_diff": []} for n in preds if n != model}
    for _ in range(n_boot):
        idx = np.concatenate([bloques[i] for i in rng.integers(0, len(bloques), len(bloques))])
        yb = y[idx]
        if yb.min() == yb.max():
            continue
        res = {n: point_metrics(yb, p[idx]) for n, p in preds.items()}
        for n, r in res.items():
            for k in METRICS:
                muestras[n][k].append(r[k])
            muestras[n]["bss"].append(1 - r["brier"] / res[reference]["brier"])
        for n in diffs:
            diffs[n]["brier_diff"].append(res[model]["brier"] - res[n]["brier"])
            diffs[n]["log_loss_diff"].append(res[model]["log_loss"] - res[n]["log_loss"])

    def ic(v):
        return [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]

    return {
        "ci95": {n: {k: ic(v) for k, v in m.items()} for n, m in muestras.items()},
        "paired_vs_model": {
            n: {k: {"ci95": ic(v), "mean": round(float(np.mean(v)), 4)} for k, v in d.items()} for n, d in diffs.items()
        },
    }


def alert_levels(y: np.ndarray, p: np.ndarray, amarillo: float, rojo: float) -> dict:
    y = np.asarray(y, dtype=int)
    nivel = np.where(p > rojo, "ROJO", np.where(p >= amarillo, "AMARILLO", "VERDE"))
    niveles = {}
    for n in ("VERDE", "AMARILLO", "ROJO"):
        m = nivel == n
        niveles[n] = {
            "share": round(float(m.mean()), 4),
            "rain_rate": round(float(y[m].mean()), 4) if m.any() else None,
        }

    def pr(alerta):
        return {
            "precision": round(float(precision_score(y, alerta, zero_division=0)), 4),
            "recall": round(float(recall_score(y, alerta, zero_division=0)), 4),
        }

    return {"levels": niveles, "ge_amarillo": pr(p >= amarillo), "rojo": pr(p > rojo)}


def external_validation(
    obs_rain: np.ndarray, p_model: np.ndarray, forecast_mm: np.ndarray, reference_mm: np.ndarray, amarillo: float
) -> dict:
    """Modelo frente a lluvia medida por pluviómetros (spec 005, US4)."""
    obs = np.asarray(obs_rain, dtype=int)
    return {
        "n": int(len(obs)),
        "rain_rate_obs": round(float(obs.mean()), 4),
        "roc_auc": {
            "model": round(float(roc_auc_score(obs, p_model)), 4),
            "raw_forecast_mm": round(float(roc_auc_score(obs, forecast_mm)), 4),
            "label_reference_mm": round(float(roc_auc_score(obs, reference_mm)), 4),
        },
        "kappa_model_at_amarillo": round(float(cohen_kappa_score(obs, p_model >= amarillo)), 4),
    }
