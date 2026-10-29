import pandas as pd

from mdva.modeling import splits


def _horas():
    return pd.Series(pd.date_range("2022-01-01", "2025-12-31 23:00", freq="h", tz="UTC"))


def test_splits_disjuntos_y_con_separacion_de_24_horas():
    t = _horas()
    m = splits.temporal_splits(t)
    assert not (m["train"] & m["validation"]).any() and not (m["validation"] & m["test"]).any()
    assert not (m["train"] & m["external"]).any()
    assert t[m["train"]].max() == pd.Timestamp("2023-12-31 23:00", tz="UTC")
    assert t[m["validation"]].min() == pd.Timestamp("2024-01-02 00:00", tz="UTC")
    assert t[m["test"]].min() == pd.Timestamp("2025-01-02 00:00", tz="UTC")
    assert t[m["test"]].max() == pd.Timestamp("2025-12-31 23:00", tz="UTC")


def test_junio_y_julio_2022_reservados_para_validacion_externa():
    t = _horas()
    m = splits.temporal_splits(t)
    externos = t[m["external"]]
    assert externos.min() == pd.Timestamp("2022-06-01", tz="UTC")
    assert externos.max() == pd.Timestamp("2022-07-31 23:00", tz="UTC")
    assert m["train"].sum() == 2 * 8760 - 61 * 24


def test_describe_reporta_periodos_y_tasas():
    t = _horas()
    y = pd.Series((t.dt.hour == 15).astype(int))
    d = splits.describe(t, y, splits.temporal_splits(t))
    assert d["test"]["rows"] == 364 * 24
    assert d["validation"]["rain_rate"] == round(1 / 24, 4)
    assert d["train"]["excluded"][0].startswith("2022-06-01")
