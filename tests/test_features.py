import re

import numpy as np
import pandas as pd
import pytest

from mdva import config
from mdva.features import FEATURES, FeatureInputError, build_features, validate_inputs

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


def test_depresion_del_punto_de_rocio_y_log1p():
    f = build_features(_con(precipitation=0.0, cape=0.0)).iloc[0]
    assert f["dew_point_depression"] == pytest.approx(2.6)
    assert f["precipitation_log1p"] == 0 and f["cape_log1p"] == 0


# ── US1: paridad entrenamiento / inferencia ──────────────────────────────────


def _como_peticion(df: pd.DataFrame) -> list[dict]:
    """Convierte filas del dataset en registros como llegarían por HTTP (JSON)."""
    registros = df[["time_utc", *config.FORECAST_VARIABLES]].copy()
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
        }
    )
    assert _paridad(df) == 0.0


@pytest.mark.skipif(not config.DATASET_PROCESSED.exists(), reason="dataset real no construido (make data)")
def test_paridad_con_el_dataset_real():
    df = pd.read_parquet(config.DATASET_PROCESSED).sample(1000, random_state=0)
    assert _paridad(df) == 0.0


# ── US3: documentación sincronizada ──────────────────────────────────────────


def test_documentacion_lista_las_features_en_orden():
    doc = (config.PROJ_ROOT / "docs" / "features.md").read_text(encoding="utf-8")
    tabla = re.findall(r"^\|\s*\d+\s*\|\s*`([a-z0-9_]+)`", doc, flags=re.MULTILINE)
    assert tabla == list(FEATURES)
