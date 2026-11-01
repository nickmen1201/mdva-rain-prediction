"""Análisis del estudio: permutación, PDP, segmentos, calibración cross-fitted y costos (spec 012)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression

from mdva.modeling import analysis, cv


@pytest.fixture(scope="module")
def datos():
    rng = np.random.default_rng(0)
    t = pd.Series(pd.date_range("2022-01-01", "2025-01-01", freq="6h", tz="UTC", inclusive="left"))
    n = len(t)
    X = pd.DataFrame({"senal": rng.normal(size=n), "ruido": rng.normal(size=n)})
    y = (rng.random(n) < 1 / (1 + np.exp(-(2 * X["senal"] - 1)))).astype(int)
    return t, X, y.to_numpy()


def test_permutacion_ordena_senal_sobre_ruido(datos):
    t, X, y = datos
    folds = cv.rolling_folds(t)[:2]
    fitted = [LogisticRegression().fit(X.iloc[f.train], y[f.train]) for f in folds]
    imp = analysis.permutation_importances(fitted, X, y, folds, n_repeats=3)
    assert imp[0]["feature"] == "senal" and imp[0]["mean"] > 0.1
    ruido = next(r for r in imp if r["feature"] == "ruido")
    assert ruido["ci95"][0] <= 0 <= ruido["ci95"][1] + 1e-3


def test_pdp_detecta_tendencia(datos):
    _, X, y = datos
    est = LogisticRegression().fit(X, y)
    pd_ = analysis.partial_dependences(est, X, ["senal"], grid_resolution=10)
    assert pd_["senal"]["trend"] == "creciente" and len(pd_["senal"]["grid"]) == 10


def test_temporadas():
    s = analysis.season(pd.Series([1, 3, 4, 7, 10, 12]))
    assert s.tolist() == ["seca", "transición", "lluviosa", "seca", "lluviosa", "seca"]


def test_segmentos_sin_positivos_no_inventan_metricas():
    y = np.array([0, 0, 1, 0, 1, 1])
    p = np.array([0.1, 0.2, 0.7, 0.3, 0.8, 0.6])
    seg = pd.Series(["a", "a", "b", "b", "b", "b"])
    filas = {f["segment"]: f for f in analysis.segment_metrics(y, p, seg)}
    assert "roc_auc" not in filas["a"] and filas["a"]["n"] == 2
    assert filas["b"]["roc_auc"] == pytest.approx(1.0)


def test_calibracion_crossfit_corrige_un_sesgo_y_no_mira_el_fold(datos):
    t, _, y = datos
    folds = cv.rolling_folds(t)
    oof = np.full(len(y), np.nan)
    rng = np.random.default_rng(1)
    for f in folds:  # probabilidades sesgadas al alza
        oof[f.valid] = np.clip(0.3 + 0.4 * y[f.valid] + rng.normal(0, 0.1, len(f.valid)) + 0.15, 0.01, 0.99)
    r = analysis.crossfit_calibration(y, oof, folds)
    assert r["chosen"] in ("isotonic", "sigmoid")
    assert r["methods"][r["chosen"]]["ece"] < r["methods"]["none"]["ece"]
    assert r["evaluated_folds"] == [f.name for f in folds[1:]]


def test_costos_umbral_teorico_con_probabilidades_calibradas():
    rng = np.random.default_rng(2)
    p = rng.random(200_000)
    y = (rng.random(200_000) < p).astype(int)  # calibradas por construcción
    c = analysis.cost_curves(y, p, ratios=(1, 3))
    assert c["ratios"]["1"]["optimal_threshold"] == pytest.approx(0.5, abs=0.03)
    assert c["ratios"]["3"]["optimal_threshold"] == pytest.approx(0.25, abs=0.03)
    assert c["ratios"]["1"]["business_thresholds"]["0.4"]["regret_vs_optimal"] >= 0
