"""Validación cruzada temporal *rolling origin* dentro del periodo de desarrollo (spec 012, R-45).

Cada fold valida un trimestre y entrena con todo lo anterior (ventana creciente), dejando un hueco
de 24 h entre ambos para que la autocorrelación horaria no filtre información. Solo se usan datos de
desarrollo (2022–2024 sin el periodo de validación externa SIATA); 2025 y 2026 nunca entran aquí.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

from mdva.modeling import evaluate, splits

# Inicio de cada trimestre de validación (6 folds: 2023-T3 … 2024-T4)
FOLD_STARTS = tuple(
    pd.Timestamp(s, tz="UTC")
    for s in ("2023-07-01", "2023-10-01", "2024-01-01", "2024-04-01", "2024-07-01", "2024-10-01")
)
DEV_END = pd.Timestamp("2025-01-01", tz="UTC")


@dataclass(frozen=True)
class Fold:
    name: str
    train: np.ndarray  # índices posicionales
    valid: np.ndarray


def development_mask(time_utc: pd.Series) -> np.ndarray:
    """2022–2024 sin el periodo reservado a la validación externa (jun–jul 2022)."""
    t = time_utc
    externo = (t >= splits.EXTERNAL[0]) & (t < splits.EXTERNAL[1])
    return ((t >= splits.TRAIN[0]) & (t < DEV_END) & ~externo).to_numpy()


def rolling_folds(time_utc: pd.Series, starts=FOLD_STARTS, gap: pd.Timedelta = splits.GAP) -> list[Fold]:
    t = time_utc.reset_index(drop=True)
    dev = development_mask(t)
    bordes = (*starts, DEV_END)
    folds = []
    for i, inicio in enumerate(starts):
        fin = bordes[i + 1]
        train = np.flatnonzero(dev & (t < inicio - gap).to_numpy())
        valid = np.flatnonzero(dev & (t >= inicio).to_numpy() & (t < fin).to_numpy())
        folds.append(Fold(f"{inicio.year}-T{(inicio.month - 1) // 3 + 1}", train, valid))
    return folds


def fold_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    p = np.clip(p, evaluate.EPS, 1 - evaluate.EPS)
    return {
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "brier": float(brier_score_loss(y, p)),
        "roc_auc": float(roc_auc_score(y, p)) if 0 < y.sum() < len(y) else float("nan"),
    }


@dataclass
class CVResult:
    per_fold: list[dict]
    oof: np.ndarray  # predicción out-of-fold (NaN fuera de los folds de validación)

    @property
    def mean(self) -> dict:
        return {k: float(np.nanmean([f[k] for f in self.per_fold])) for k in ("log_loss", "brier", "roc_auc")}

    @property
    def std(self) -> dict:
        return {k: float(np.nanstd([f[k] for f in self.per_fold], ddof=1)) for k in ("log_loss", "brier", "roc_auc")}

    @property
    def se_log_loss(self) -> float:
        return self.std["log_loss"] / np.sqrt(len(self.per_fold))

    def summary(self) -> dict:
        return {
            "mean": {k: round(v, 5) for k, v in self.mean.items()},
            "std": {k: round(v, 5) for k, v in self.std.items()},
            "se_log_loss": round(self.se_log_loss, 5),
            "per_fold": [
                {k: (round(v, 5) if isinstance(v, float) else v) for k, v in f.items()} for f in self.per_fold
            ],
        }


def cross_validate(
    estimator,
    X: pd.DataFrame,
    y: np.ndarray,
    folds: list[Fold],
    *,
    transform: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None = None,
) -> CVResult:
    """Ajusta un clon por fold y devuelve métricas por fold y predicciones out-of-fold.

    `transform(p_valid, train_idx, valid_idx)` permite post-procesar (p. ej. calibrar con datos
    anteriores al fold) sin mirar el fold de validación.
    """
    oof = np.full(len(y), np.nan)
    per_fold = []
    for f in folds:
        est = clone(estimator).fit(X.iloc[f.train], y[f.train])
        p = est.predict_proba(X.iloc[f.valid])[:, 1]
        if transform is not None:
            p = transform(p, f.train, f.valid)
        oof[f.valid] = p
        per_fold.append({"fold": f.name, "n_valid": int(len(f.valid)), **fold_metrics(y[f.valid], p)})
    return CVResult(per_fold, oof)
