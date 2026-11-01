"""Calibración post-hoc serializable (spec 012, R-49).

El mapa de calibración se ajusta sobre predicciones *out-of-fold* (cross-fitting temporal), no sobre
datos que el modelo vio al entrenar; el modelo final se entrena en todo desarrollo y se le aplica el
mismo mapa. Clases simples (sin lambdas) para que `joblib` pueda guardarlas con el modelo.
"""

from __future__ import annotations

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from mdva.modeling.evaluate import EPS

METHODS = ("none", "isotonic", "sigmoid")


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    return np.log(p / (1 - p)).reshape(-1, 1)


class Calibrator:
    """Mapa p → p calibrada. `none` = identidad; `isotonic`; `sigmoid` (Platt sobre el logit)."""

    def __init__(self, method: str):
        if method not in METHODS:
            raise ValueError(f"método de calibración desconocido: {method}")
        self.method = method
        self.model_ = None

    def fit(self, p: np.ndarray, y: np.ndarray) -> Calibrator:
        if self.method == "isotonic":
            self.model_ = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(p, y)
        elif self.method == "sigmoid":
            self.model_ = LogisticRegression(C=1e6, max_iter=1000).fit(_logit(p), y)
        return self

    def __call__(self, p: np.ndarray) -> np.ndarray:
        p = np.asarray(p, dtype=float)
        if self.method == "isotonic":
            q = self.model_.predict(p)
        elif self.method == "sigmoid":
            q = self.model_.predict_proba(_logit(p))[:, 1]
        else:
            q = p
        return np.clip(q, EPS, 1 - EPS)


class CalibratedModel:
    """Estimador base + mapa de calibración, con la interfaz `predict_proba` de scikit-learn."""

    def __init__(self, base, calibrator: Calibrator):
        self.base = base
        self.calibrator = calibrator

    @property
    def feature_names_in_(self):
        return self.base.feature_names_in_

    def predict_proba(self, X) -> np.ndarray:
        q = self.calibrator(self.base.predict_proba(X)[:, 1])
        return np.column_stack([1 - q, q])
