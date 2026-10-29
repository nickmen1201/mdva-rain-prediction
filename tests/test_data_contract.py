import dataclasses
import json

import numpy as np
import pandas as pd
import pytest

from mdva import config
from mdva.data_contract import (
    DATASET_CONTRACT,
    EXPECTED_FORECAST_UNITS,
    DataContractError,
    validate,
    validate_units,
)

HORAS = 48
CONTRACT = dataclasses.replace(
    DATASET_CONTRACT,
    period_start=pd.Timestamp("2022-01-01T00:00", tz="UTC"),
    period_end=pd.Timestamp("2022-01-01T00:00", tz="UTC") + pd.Timedelta(hours=HORAS - 1),
)


@pytest.fixture
def valido():
    tiempos = pd.date_range("2022-01-01", periods=HORAS, freq="h", tz="UTC")
    filas = []
    for sid, lat, lon in [(59, 6.21, -75.56), (68, 6.27, -75.56)]:
        filas.append(
            pd.DataFrame(
                {
                    "station_id": np.int64(sid),
                    "time_utc": tiempos,
                    "latitude": lat,
                    "longitude": lon,
                    "temperature_2m": 20.0,
                    "relative_humidity_2m": 80.0,
                    "dew_point_2m": 16.0,
                    "cloud_cover": 50.0,
                    "wind_speed_10m": 2.0,
                    "wind_direction_10m": 180.0,
                    "pressure_msl": 1012.0,
                    "precipitation": 0.0,
                    "cape": 100.0,
                    "precipitation_ref": 0.0,
                    "era5_cell": "6.25,-75.5",
                    "rain": False,
                }
            )
        )
    return pd.concat(filas, ignore_index=True)


def test_dataset_valido_pasa(valido):
    report = validate(valido, CONTRACT)
    assert report.ok
    assert report.rows == 2 * HORAS


def test_fuera_de_rango_falla(valido):
    valido.loc[3, "relative_humidity_2m"] = 150.0
    with pytest.raises(DataContractError, match="range:relative_humidity_2m"):
        validate(valido, CONTRACT)


def test_unidad_distinta_falla():
    unidades = dict(EXPECTED_FORECAST_UNITS, wind_speed_10m="km/h")
    with pytest.raises(DataContractError, match="wind_speed_10m: recibido 'km/h'"):
        validate_units(unidades, EXPECTED_FORECAST_UNITS, "forecast")


def test_unidades_correctas_pasan():
    validate_units(dict(EXPECTED_FORECAST_UNITS, time="iso8601"), EXPECTED_FORECAST_UNITS, "forecast")


def test_duplicado_falla(valido):
    duplicado = pd.concat([valido, valido.iloc[[0]]], ignore_index=True)
    with pytest.raises(DataContractError, match="unique_key"):
        validate(duplicado, CONTRACT)


def test_horas_faltantes_por_encima_del_tolerado_fallan(valido):
    incompleto = valido.drop(index=range(0, 5))  # 5 de 48 horas (> 1 %) en la estación 59
    with pytest.raises(DataContractError, match="coverage"):
        validate(incompleto, CONTRACT)


def test_columna_faltante_falla(valido):
    with pytest.raises(DataContractError, match="faltan=\\['cape'\\]"):
        validate(valido.drop(columns="cape"), CONTRACT)


def test_nulo_en_columna_no_nullable_falla(valido):
    valido.loc[0, "temperature_2m"] = np.nan
    with pytest.raises(DataContractError, match="nulls:temperature_2m"):
        validate(valido, CONTRACT)


def test_fuera_del_periodo_falla(valido):
    valido.loc[0, "time_utc"] = pd.Timestamp("2030-01-01", tz="UTC")
    with pytest.raises(DataContractError, match="period"):
        validate(valido, CONTRACT)


def test_reporte_sin_lanzar_lista_todas_las_fallas(valido):
    valido.loc[0, "cloud_cover"] = -1.0
    valido.loc[1, "cape"] = 20000.0
    report = validate(valido, CONTRACT, raise_on_error=False)
    assert not report.ok
    assert {r.rule for r in report.failures()} == {"range:cloud_cover", "range:cape"}


def test_contrato_en_codigo_coincide_con_el_de_la_spec():
    spec = json.loads(
        (config.PROJ_ROOT / "specs" / "003-openmeteo-dataset" / "contracts" / "rain_hourly.v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert spec["version"] == DATASET_CONTRACT.version
    assert tuple(spec["primary_key"]) == DATASET_CONTRACT.primary_key
    codigo = [(c.name, c.dtype, c.min, c.max, c.nullable) for c in DATASET_CONTRACT.columns]
    json_cols = [(c["name"], c["dtype"], c.get("min"), c.get("max"), c["nullable"]) for c in spec["columns"]]
    assert codigo == json_cols
    assert DATASET_CONTRACT.expected_hours == 35064
