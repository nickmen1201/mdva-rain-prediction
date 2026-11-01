"""Búsqueda de hiperparámetros con validación cruzada temporal (spec 012, R-45).

- HistGradientBoosting: búsqueda aleatoria con semilla fija sobre un espacio declarado.
- Familias de referencia con una grilla pequeña: regresión logística con *splines* (un GAM aditivo
  simple) y bosque aleatorio (la familia del modelo heredado).
- Objetivo: log loss medio entre folds. Elección final con la regla de "un error estándar": entre las
  configuraciones a ≤ 1 EE de la mejor, la de menor complejidad.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import SplineTransformer, StandardScaler

from mdva.modeling import cv

log = logging.getLogger(__name__)

SEED = 42

# Espacio de búsqueda de HGB (declarado, R-45)
HGB_SPACE = {
    "learning_rate": ("loguniform", 0.02, 0.3),
    "max_leaf_nodes": ("int_loguniform", 7, 63),
    "min_samples_leaf": ("choice", (20, 50, 100, 200, 400)),
    "l2_regularization": ("loguniform", 1e-3, 10.0),
    "max_features": ("uniform", 0.5, 1.0),
    "max_iter": ("int_uniform", 100, 800),
}
N_HGB_TRIALS = 60

# Configuración de la versión 1.0.0 (spec 005), evaluada con la misma CV como punto de comparación
V1_PARAMS = {"learning_rate": 0.1, "max_leaf_nodes": 15, "max_iter": 400, "l2_regularization": 1.0}

SPLINE_GRID = [{"n_knots": 6, "C": c} for c in (0.1, 1.0)]
RF_GRID = [{"max_depth": d, "min_samples_leaf": m} for d in (12, None) for m in (20, 100)]


def sample_space(space: dict, n: int, seed: int = SEED) -> list[dict]:
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        params = {}
        for nombre, (tipo, *args) in space.items():
            if tipo == "loguniform":
                params[nombre] = float(np.exp(rng.uniform(np.log(args[0]), np.log(args[1]))))
            elif tipo == "int_loguniform":
                params[nombre] = int(round(np.exp(rng.uniform(np.log(args[0]), np.log(args[1])))))
            elif tipo == "uniform":
                params[nombre] = float(rng.uniform(args[0], args[1]))
            elif tipo == "int_uniform":
                params[nombre] = int(rng.integers(args[0], args[1] + 1))
            elif tipo == "choice":
                params[nombre] = args[0][int(rng.integers(len(args[0])))]
            else:
                raise ValueError(f"tipo de distribución desconocido: {tipo}")
        out.append({k: (round(v, 6) if isinstance(v, float) else v) for k, v in params.items()})
    return out


def make_hgb(params: dict) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(early_stopping=False, random_state=SEED, **params)


def make_spline_logistic(params: dict):
    return make_pipeline(
        SplineTransformer(n_knots=params["n_knots"], degree=3),
        StandardScaler(),
        LogisticRegression(C=params["C"], max_iter=1000),
    )


def make_rf(params: dict) -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=150, max_samples=0.3, max_features="sqrt", n_jobs=-1, random_state=SEED, **params
    )


FAMILIES = {"hgb": make_hgb, "spline_logistic": make_spline_logistic, "random_forest": make_rf}


def complexity(family: str, params: dict) -> float:
    """Proxy de complejidad para la regla de un error estándar (menor = más simple)."""
    if family.startswith("hgb"):
        return params["max_iter"] * params["max_leaf_nodes"]
    if family == "random_forest":
        return 150 * (2 ** (params["max_depth"] or 30)) / params["min_samples_leaf"]
    return params["n_knots"] / params["C"]


@dataclass
class Trial:
    family: str
    params: dict
    cv: cv.CVResult = field(repr=False)
    seconds: float

    def row(self) -> dict:
        return {
            "family": self.family,
            "params": self.params,
            **self.cv.summary(),
            "complexity": complexity(self.family, self.params),
            "seconds": round(self.seconds, 1),
        }


def run_trial(family: str, params: dict, X, y, folds) -> Trial:
    t0 = time.time()
    r = cv.cross_validate(FAMILIES[family](params), X, y, folds)
    trial = Trial(family, params, r, time.time() - t0)
    log.info("%s %s → log loss %.5f ± %.5f (%.0f s)", family, params, r.mean["log_loss"], r.se_log_loss, trial.seconds)
    return trial


def paired_delta(best: Trial, other: Trial) -> tuple[float, float]:
    """Media y EE de la diferencia de log loss por fold (other − best). Los folds son los mismos para todos
    los ensayos, así que la comparación pareada elimina la variación entre trimestres (que domina el EE de
    la media: los folds difieren mucho en tasa de lluvia)."""
    d = np.array([o["log_loss"] - b["log_loss"] for o, b in zip(other.cv.per_fold, best.cv.per_fold, strict=True)])
    return float(d.mean()), float(d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 1 else 0.0


def one_standard_error(trials: list[Trial]) -> tuple[Trial, Trial]:
    """(mejor por log loss medio, elegido por la regla de un EE **pareada** entre los de la misma familia).

    Elegible: la diferencia media con la mejor no supera su propio EE pareado. Entre los elegibles, el de
    menor complejidad.
    """
    mejor = min(trials, key=lambda t: t.cv.mean["log_loss"])
    cercanos = []
    for t in trials:
        if t.family != mejor.family:
            continue
        media, ee = paired_delta(mejor, t)
        if media <= ee:
            cercanos.append(t)
    elegido = min(cercanos, key=lambda t: (complexity(t.family, t.params), t.cv.mean["log_loss"]))
    return mejor, elegido


def search(X, y, folds, *, n_hgb: int = N_HGB_TRIALS, seed: int = SEED, quick: bool = False) -> dict:
    """`quick` (tests y verificación del pipeline): una sola configuración por familia de referencia."""
    trials = [run_trial("hgb", V1_PARAMS | {"max_features": 1.0, "min_samples_leaf": 20}, X, y, folds)]
    trials[0].family = "hgb_v1"  # referencia: configuración de la versión 1.0.0
    trials += [run_trial("hgb", p, X, y, folds) for p in sample_space(HGB_SPACE, n_hgb, seed)]
    trials += [run_trial("spline_logistic", p, X, y, folds) for p in SPLINE_GRID[: 1 if quick else None]]
    trials += [run_trial("random_forest", p, X, y, folds) for p in RF_GRID[: 1 if quick else None]]
    mejor, elegido = one_standard_error([t for t in trials if t.family != "hgb_v1"])
    return {"trials": trials, "best": mejor, "chosen": elegido, "v1": trials[0]}
