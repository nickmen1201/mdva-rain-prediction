import re

import numpy as np
import pandas as pd
import pytest

from mdva import config
from mdva.features import (
    BASE_FEATURES,
    FEATURES,
    RAW_INPUTS,
    WINDOW_INPUTS,
    FeatureInputError,
    build_features,
    forecast_window_inputs,
    validate_inputs,
)

ENTRADA = {
    "time_utc": "2026-10-28T20:00:00Z",
    "temperature_2m": 19.0,
    "relative_humidity_2m": 85.0,
    "dew_point_2m": 16.4,
    "cloud_cover": 90.0,
    "wind_speed_10m": 2.0,
    "wind_direction_10m": 180.0,
    "pressure_msl": 1013.0,
    "precipitation": 0.4,
    "cape": 300.0,
    # Ventana del pronóstico y ubicación (contrato 1.1.0)
    "precipitation_prev2": 0.0,
    "precipitation_prev1": 0.1,
    "precipitation_next1": 1.2,
    "precipitation_next2": 0.8,
    "cloud_cover_prev1": 70.0,
    "cloud_cover_next1": 95.0,
    "cape_prev1": 250.0,
    "cape_next1": 350.0,
    "latitude": 6.2518,
    "longitude": -75.5636,
}


def _con(**cambios):
    return [dict(ENTRADA, **cambios)]


# ── US2: validación de entradas ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "registro,campo,regla",
    [
        ({k: v for k, v in ENTRADA.items() if k != "cape"}, "cape", "campo faltante"),
        (dict(ENTRADA, temperature_2m=None), "temperature_2m", "nulo"),
        (dict(ENTRADA, relative_humidity_2m=150.0), "relative_humidity_2m", "fuera de rango"),
        (dict(ENTRADA, wind_speed_10m=-1.0), "wind_speed_10m", "fuera de rango"),
        (dict(ENTRADA, cloud_cover="mucha"), "cloud_cover", "no numérico"),
        (dict(ENTRADA, time_utc="2026-10-28T20:00:00"), "time_utc", "sin zona horaria"),
        (dict(ENTRADA, time_utc="ayer"), "time_utc", "ISO 8601"),
        (dict(ENTRADA, time_utc=None), "time_utc", "nulo"),
        ({k: v for k, v in ENTRADA.items() if k != "precipitation_next1"}, "precipitation_next1", "campo faltante"),
        (dict(ENTRADA, cloud_cover_prev1=120.0), "cloud_cover_prev1", "fuera de rango"),
        (dict(ENTRADA, latitude=4.6), "latitude", "fuera de rango"),  # Bogotá: fuera del valle
    ],
)
def test_entradas_invalidas_se_rechazan_nombrando_campo(registro, campo, regla):
    with pytest.raises(FeatureInputError) as e:
        validate_inputs([registro])
    assert any(c == campo and regla in r for c, r in e.value.problems), e.value.problems


def test_reune_todos_los_problemas():
    with pytest.raises(FeatureInputError) as e:
        validate_inputs(_con(cloud_cover=-5.0, cape=1e6))
    assert {c for c, _ in e.value.problems} == {"cloud_cover", "cape"}


def test_zona_horaria_explicita_se_normaliza_a_utc():
    a = validate_inputs(_con(time_utc="2026-10-28T15:00:00-05:00"))
    b = validate_inputs(_con(time_utc="2026-10-28T20:00:00Z"))
    assert a["time_utc"].iloc[0] == b["time_utc"].iloc[0] == pd.Timestamp("2026-10-28T20:00", tz="UTC")


def test_columnas_extra_se_ignoran():
    assert list(build_features(_con(estacion="x")).columns) == list(FEATURES)


# ── US1: transformaciones ────────────────────────────────────────────────────


def test_hora_y_mes_son_locales_de_bogota():
    f = build_features(_con(time_utc="2026-01-01T03:00:00Z"))  # 31-dic 22:00 en Bogotá
    hora, mes = 22, 12
    assert f["hour_sin"].iloc[0] == pytest.approx(np.sin(2 * np.pi * hora / 24))
    assert f["hour_cos"].iloc[0] == pytest.approx(np.cos(2 * np.pi * hora / 24))
    assert f["month_sin"].iloc[0] == pytest.approx(np.sin(2 * np.pi * (mes - 1) / 12))


def test_componentes_del_viento():
    norte = build_features(_con(wind_direction_10m=0.0, wind_speed_10m=3.0)).iloc[0]
    assert norte["wind_u"] == pytest.approx(0.0, abs=1e-12) and norte["wind_v"] == pytest.approx(-3.0)
    este = build_features(_con(wind_direction_10m=90.0, wind_speed_10m=3.0)).iloc[0]
    assert este["wind_u"] == pytest.approx(-3.0) and este["wind_v"] == pytest.approx(0.0, abs=1e-12)


def test_0_y_360_grados_son_iguales_y_la_calma_vale_cero():
    a = build_features(_con(wind_direction_10m=0.0))
    b = build_features(_con(wind_direction_10m=360.0))
    assert np.allclose(a[["wind_u", "wind_v"]], b[["wind_u", "wind_v"]])
    calma = build_features(_con(wind_speed_10m=0.0, wind_direction_10m=123.0)).iloc[0]
    assert calma["wind_u"] == 0 and calma["wind_v"] == 0


def test_ventana_del_pronostico_y_ubicacion():
    f = build_features([ENTRADA]).iloc[0]
    assert f["precipitation_next1_log1p"] == pytest.approx(np.log1p(1.2))
    assert f["cloud_cover_prev1"] == 70.0 and f["cape_next1_log1p"] == pytest.approx(np.log1p(350.0))
    assert f["precipitation_5h_log1p"] == pytest.approx(np.log1p(0.0 + 0.1 + 0.4 + 1.2 + 0.8))
    assert f["latitude"] == 6.2518 and f["longitude"] == -75.5636


def test_las_13_features_base_no_cambian_respecto_del_contrato_1_0():
    assert FEATURES[: len(BASE_FEATURES)] == BASE_FEATURES and len(BASE_FEATURES) == 13
    assert len(FEATURES) == 24 and len(RAW_INPUTS) == 9 + 8 + 2


def test_ventana_desde_la_serie_por_estacion_sin_cruzar_ni_saltar_huecos():
    t = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
    filas = [
        {"station_id": s, "time_utc": ti, "precipitation": base + i, "cloud_cover": base + 10 * i, "cape": base + i}
        for s, base in ((1, 0.0), (2, 100.0))
        for i, ti in enumerate(t)
        if not (s == 2 and i == 2)  # hueco de una hora en la estación 2
    ]
    df = pd.DataFrame(filas).sample(frac=1, random_state=0)
    w = forecast_window_inputs(df)
    assert set(w.columns) == set(WINDOW_INPUTS) and list(w.index) == list(df.index)

    def fila(s, i):
        return df[(df.station_id == s) & (df.time_utc == t[i])].index[0]

    assert w.loc[fila(1, 2), "precipitation_prev1"] == 1 and w.loc[fila(1, 2), "precipitation_next2"] == 4
    assert w.loc[fila(1, 2), "cloud_cover_next1"] == 30
    assert np.isnan(w.loc[fila(2, 1), "precipitation_next1"])  # la hora 2 no existe: no se toma la 3
    assert np.isnan(w.loc[fila(1, 0), "precipitation_prev1"])  # borde de la serie


def test_depresion_del_punto_de_rocio_y_log1p():
    f = build_features(_con(precipitation=0.0, cape=0.0)).iloc[0]
    assert f["dew_point_depression"] == pytest.approx(2.6)
    assert f["precipitation_log1p"] == 0 and f["cape_log1p"] == 0


# ── US1: paridad entrenamiento / inferencia ──────────────────────────────────


def _como_peticion(df: pd.DataFrame) -> list[dict]:
    """Convierte filas del dataset en registros como llegarían por HTTP (JSON)."""
    registros = df[["time_utc", *[c for c in RAW_INPUTS]]].copy()
    registros["time_utc"] = registros["time_utc"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return [{k: (float(v) if k != "time_utc" else v) for k, v in r.items()} for r in registros.to_dict("records")]


def _paridad(df: pd.DataFrame) -> float:
    entrenamiento = build_features(df).reset_index(drop=True)
    inferencia = build_features(_como_peticion(df))
    assert list(entrenamiento.columns) == list(inferencia.columns) == list(FEATURES)
    return float((entrenamiento - inferencia).abs().to_numpy().max())


def test_paridad_con_datos_sinteticos():
    rng = np.random.default_rng(0)
    n = 500
    df = pd.DataFrame(
        {
            "time_utc": pd.date_range("2022-01-01", periods=n, freq="7h", tz="UTC"),
            "temperature_2m": rng.uniform(5, 30, n),
            "relative_humidity_2m": rng.uniform(20, 100, n),
            "dew_point_2m": rng.uniform(0, 20, n),
            "cloud_cover": rng.uniform(0, 100, n),
            "wind_speed_10m": rng.uniform(0, 5, n),
            "wind_direction_10m": rng.uniform(0, 360, n),
            "pressure_msl": rng.uniform(1005, 1020, n),
            "precipitation": rng.exponential(0.3, n),
            "cape": rng.exponential(200, n),
            **{c: rng.exponential(0.3, n) for c in WINDOW_INPUTS if c.startswith("precipitation")},
            **{c: rng.uniform(0, 100, n) for c in WINDOW_INPUTS if c.startswith("cloud_cover")},
            **{c: rng.exponential(200, n) for c in WINDOW_INPUTS if c.startswith("cape")},
            "latitude": rng.uniform(6.1, 6.4, n),
            "longitude": rng.uniform(-75.7, -75.4, n),
        }
    )
    assert _paridad(df) == 0.0


@pytest.mark.skipif(not config.DATASET_PROCESSED.exists(), reason="dataset real no construido (make data)")
def test_paridad_con_el_dataset_real():
    df = pd.read_parquet(config.DATASET_PROCESSED)
    df = pd.concat([df, forecast_window_inputs(df)], axis=1).dropna().sample(1000, random_state=0)
    assert _paridad(df) == 0.0


# ── US3: documentación sincronizada ──────────────────────────────────────────


def test_documentacion_lista_las_features_en_orden():
    doc = (config.PROJ_ROOT / "docs" / "features.md").read_text(encoding="utf-8")
    tabla = re.findall(r"^\|\s*\d+\s*\|\s*`([a-z0-9_]+)`", doc, flags=re.MULTILINE)
    assert tabla == list(FEATURES)
