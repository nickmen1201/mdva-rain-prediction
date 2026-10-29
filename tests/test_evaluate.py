import numpy as np
import pytest

from mdva.modeling import evaluate


def test_ece_cero_si_las_probabilidades_son_exactas():
    rng = np.random.default_rng(0)
    p = rng.uniform(0, 1, 200_000)
    y = (rng.uniform(0, 1, p.size) < p).astype(int)
    assert evaluate.expected_calibration_error(y, p) < 0.01
    assert evaluate.expected_calibration_error(y, np.full(p.size, 0.9)) > 0.3


def test_metricas_puntuales_y_recorte_de_extremos():
    y = np.array([0, 0, 1, 1])
    m = evaluate.point_metrics(y, np.array([0.0, 0.1, 0.9, 1.0]))
    assert m["roc_auc"] == 1.0 and m["pr_auc"] == 1.0
    assert np.isfinite(m["log_loss"]) and m["brier"] == pytest.approx(0.005)


def test_confiabilidad_agrupa_por_intervalos():
    filas = evaluate.reliability(np.array([0, 1, 1, 1]), np.array([0.05, 0.95, 0.92, 0.99]))
    assert [f["n"] for f in filas] == [1, 3]
    assert filas[1]["obs_rate"] == 1.0


def test_bootstrap_por_dias_da_intervalos_y_diferencias_pareadas():
    rng = np.random.default_rng(1)
    n_dias = 60
    dias = np.repeat(np.arange(n_dias), 24)
    y = (rng.uniform(size=dias.size) < 0.3).astype(int)
    bueno = np.clip(y * 0.7 + 0.15 + rng.normal(0, 0.05, y.size), 0.01, 0.99)
    preds = {"model": bueno, "climatology": np.full(y.size, 0.3)}
    r = evaluate.day_block_bootstrap(y, preds, dias, n_boot=100, seed=0)
    lo, hi = r["ci95"]["model"]["roc_auc"]
    assert 0.5 < lo <= hi <= 1.0
    assert r["paired_vs_model"]["climatology"]["brier_diff"]["ci95"][1] < 0
    assert r["ci95"]["climatology"]["bss"] == [0.0, 0.0]


def test_bootstrap_es_determinista():
    dias = np.repeat(np.arange(10), 5)
    y = np.tile([0, 1, 0, 0, 1], 10)
    preds = {"model": np.linspace(0.1, 0.9, 50), "climatology": np.full(50, 0.4)}
    a = evaluate.day_block_bootstrap(y, preds, dias, n_boot=30, seed=7)
    assert a == evaluate.day_block_bootstrap(y, preds, dias, n_boot=30, seed=7)


def test_niveles_de_alerta():
    y = np.array([0, 0, 1, 1, 1])
    p = np.array([0.1, 0.5, 0.5, 0.8, 0.39])
    r = evaluate.alert_levels(y, p, amarillo=0.40, rojo=0.70)
    assert r["levels"]["VERDE"]["share"] == 0.4 and r["levels"]["ROJO"]["rain_rate"] == 1.0
    assert r["ge_amarillo"] == {"precision": round(2 / 3, 4), "recall": round(2 / 3, 4)}
    assert r["rojo"] == {"precision": 1.0, "recall": round(1 / 3, 4)}
