"""Folds rolling-origin: sin solapamiento, con hueco y solo en desarrollo (spec 012)."""

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from mdva.modeling import cv, splits


@pytest.fixture(scope="module")
def tiempos():
    return pd.Series(pd.date_range("2022-01-01", "2026-03-01", freq="h", tz="UTC", inclusive="left"))


def test_seis_folds_trimestrales_con_hueco_de_24h(tiempos):
    folds = cv.rolling_folds(tiempos)
    assert [f.name for f in folds] == ["2023-T3", "2023-T4", "2024-T1", "2024-T2", "2024-T3", "2024-T4"]
    for f in folds:
        fin_train = tiempos.iloc[f.train].max()
        ini_valid = tiempos.iloc[f.valid].min()
        assert ini_valid - fin_train > pd.Timedelta(hours=24)
        assert not set(f.train) & set(f.valid)


def test_ventana_creciente(tiempos):
    tamanos = [len(f.train) for f in cv.rolling_folds(tiempos)]
    assert tamanos == sorted(tamanos) and len(set(tamanos)) == len(tamanos)


def test_nunca_usa_prueba_holdout_ni_validacion_externa(tiempos):
    usados = np.concatenate([np.r_[f.train, f.valid] for f in cv.rolling_folds(tiempos)])
    t = tiempos.iloc[np.unique(usados)]
    assert t.max() < pd.Timestamp("2025-01-01", tz="UTC")
    assert not ((t >= splits.EXTERNAL[0]) & (t < splits.EXTERNAL[1])).any()


def test_cross_validate_oof_y_resumen(tiempos):
    t = tiempos[tiempos < pd.Timestamp("2025-01-01", tz="UTC")].reset_index(drop=True)
    rng = np.random.default_rng(0)
    X = pd.DataFrame({"x": rng.normal(size=len(t))})
    y = (rng.random(len(t)) < 0.2).astype(int)
    folds = cv.rolling_folds(t)

    r = cv.cross_validate(DummyClassifier(strategy="prior"), X, y, folds)

    validos = np.concatenate([f.valid for f in folds])
    assert np.isfinite(r.oof[validos]).all() and np.isnan(np.delete(r.oof, validos)).all()
    assert len(r.per_fold) == 6
    assert r.mean["log_loss"] == pytest.approx(np.mean([f["log_loss"] for f in r.per_fold]))
    assert r.se_log_loss > 0
    assert set(r.summary()) == {"mean", "std", "se_log_loss", "per_fold"}


def test_transform_recibe_indices_del_fold(tiempos):
    t = tiempos[tiempos < pd.Timestamp("2025-01-01", tz="UTC")].reset_index(drop=True)
    X = pd.DataFrame({"x": np.zeros(len(t))})
    y = (np.arange(len(t)) % 5 == 0).astype(int)
    vistos = []

    def transform(p, tr, va):
        vistos.append((tr.max() < va.min()))
        return np.full_like(p, 0.5)

    r = cv.cross_validate(DummyClassifier(strategy="prior"), X, y, cv.rolling_folds(t), transform=transform)
    assert all(vistos) and r.mean["brier"] == pytest.approx(0.25)
