import numpy as np
import pandas as pd
import pytest

from mdva.modeling.baselines import Climatology, RawForecast, persistence


def test_climatologia_por_hora_local_y_mes():
    t = pd.Series(pd.date_range("2023-01-01", periods=24 * 31, freq="h", tz="UTC"))
    y = (t.dt.hour == 20).astype(int).to_numpy()  # 20 UTC = 15 h en Bogotá
    clima = Climatology().fit(t, y)
    p = clima.predict_proba(pd.Series(pd.to_datetime(["2023-01-15T20:00Z", "2023-01-15T10:00Z"], utc=True)))
    assert p.tolist() == [1.0, 0.0]


def test_climatologia_usa_tasa_global_si_no_hay_datos():
    t = pd.Series(pd.date_range("2023-01-01", periods=48, freq="h", tz="UTC"))
    clima = Climatology().fit(t, np.r_[np.ones(12), np.zeros(36)])
    assert clima.predict_proba(pd.Series(pd.to_datetime(["2023-07-01T12:00Z"], utc=True)))[0] == pytest.approx(0.25)


def test_pronostico_crudo_es_monotono_en_la_precipitacion():
    rng = np.random.default_rng(0)
    x = rng.exponential(0.5, 2000)
    y = (x + rng.normal(0, 0.3, 2000) > 0.6).astype(int)
    X = pd.DataFrame({"precipitation_log1p": np.log1p(x)})
    m = RawForecast().fit(X, y)
    p = m.predict_proba(pd.DataFrame({"precipitation_log1p": np.log1p([0.0, 0.5, 3.0])}))
    assert p[0] < p[1] < p[2]


def test_persistencia_usa_la_hora_anterior_de_la_misma_estacion():
    t = pd.Series(pd.to_datetime(["2023-01-01T00Z", "2023-01-01T01Z", "2023-01-01T00Z", "2023-01-01T01Z"], utc=True))
    s = pd.Series([1, 1, 2, 2])
    y = pd.Series([1, 0, 0, 1])
    p = persistence(s, t, y)
    assert p[1] == 1.0 and p[3] == 0.0  # hora anterior de cada estación
    assert p[0] == p[2] == 0.5  # sin hora anterior → tasa global
