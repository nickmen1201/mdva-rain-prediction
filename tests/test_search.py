"""Búsqueda de hiperparámetros: muestreo reproducible y regla de un error estándar (spec 012)."""

import numpy as np
import pytest

from mdva.modeling import cv, search


def test_muestreo_reproducible_y_dentro_del_espacio():
    a = search.sample_space(search.HGB_SPACE, 30, seed=1)
    b = search.sample_space(search.HGB_SPACE, 30, seed=1)
    assert a == b and a != search.sample_space(search.HGB_SPACE, 30, seed=2)
    for p in a:
        assert 0.02 <= p["learning_rate"] <= 0.3
        assert 7 <= p["max_leaf_nodes"] <= 63 and isinstance(p["max_leaf_nodes"], int)
        assert p["min_samples_leaf"] in (20, 50, 100, 200, 400)
        assert 1e-3 <= p["l2_regularization"] <= 10
        assert 0.5 <= p["max_features"] <= 1.0
        assert 100 <= p["max_iter"] <= 800


def _trial(family, params, lls):
    folds = [{"fold": str(i), "n_valid": 10, "log_loss": v, "brier": 0.1, "roc_auc": 0.8} for i, v in enumerate(lls)]
    return search.Trial(family, params, cv.CVResult(folds, np.array([])), 1.0)


def test_un_error_estandar_prefiere_el_mas_simple():
    grande = _trial("hgb", {"max_iter": 800, "max_leaf_nodes": 63}, [0.300, 0.302, 0.298, 0.301])
    chico = _trial("hgb", {"max_iter": 200, "max_leaf_nodes": 15}, [0.3010, 0.3005, 0.2990, 0.3008])
    malo = _trial("hgb", {"max_iter": 100, "max_leaf_nodes": 7}, [0.33, 0.34, 0.32, 0.33])
    otra = _trial("spline_logistic", {"n_knots": 5, "C": 1.0}, [0.3006, 0.3016, 0.2996, 0.3011])

    mejor, elegido = search.one_standard_error([grande, chico, malo, otra])

    assert mejor is grande
    assert elegido is chico  # dentro de 1 EE pareado, menor complejidad y de la misma familia


def test_un_error_estandar_es_pareado_entre_folds_heterogeneos():
    # Trimestres con niveles de log loss muy distintos: el EE de la media es enorme, pero el modelo
    # simple es peor en TODOS los folds; la regla pareada no debe aceptarlo.
    mejor = _trial("hgb", {"max_iter": 600, "max_leaf_nodes": 31}, [0.25, 0.38, 0.27, 0.35])
    simple = _trial("hgb", {"max_iter": 100, "max_leaf_nodes": 7}, [0.27, 0.40, 0.29, 0.37])

    _, elegido = search.one_standard_error([mejor, simple])

    assert (
        simple.cv.mean["log_loss"] - mejor.cv.mean["log_loss"] < mejor.cv.se_log_loss
    )  # el criterio ingenuo lo aceptaría
    assert elegido is mejor
    media, ee = search.paired_delta(mejor, simple)
    assert media == pytest.approx(0.02) and ee == pytest.approx(0.0)


def test_complejidad_por_familia():
    assert search.complexity("hgb", {"max_iter": 100, "max_leaf_nodes": 10}) == 1000
    assert search.complexity("hgb_v1", {"max_iter": 400, "max_leaf_nodes": 15}) == 6000
    assert search.complexity("spline_logistic", {"n_knots": 6, "C": 0.1}) > search.complexity(
        "spline_logistic", {"n_knots": 6, "C": 1.0}
    )


@pytest.mark.parametrize("family", ["hgb", "spline_logistic", "random_forest"])
def test_las_familias_se_construyen(family):
    params = {"hgb": search.V1_PARAMS, "spline_logistic": search.SPLINE_GRID[0], "random_forest": search.RF_GRID[0]}
    est = search.FAMILIES[family](params[family])
    rng = np.random.default_rng(0)
    X, y = rng.normal(size=(200, 3)), (rng.random(200) < 0.3).astype(int)
    assert est.fit(X, y).predict_proba(X).shape == (200, 2)
