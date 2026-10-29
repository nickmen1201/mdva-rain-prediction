"""Pipeline completo con un servidor Open-Meteo simulado (sin red)."""

import json
from urllib.parse import parse_qs, urlparse

import numpy as np
import pandas as pd
import pytest

from mdva import config, dataset
from mdva.data_contract import EXPECTED_FORECAST_UNITS, DataContractError

ESTACIONES = pd.DataFrame(
    {
        "codigo_estacion": [68, 59, 59],
        "estacion": ["Jardin Botanico", "ISAGEN", "ISAGEN"],
        "fecha": ["2022-06-07 17:57:00"] * 3,
        "precipitacion_mm": [0.0] * 3,
        "calidad": [1.0] * 3,
        "latitud": [6.26925, 6.21394, 6.21394],
        "longitud": [-75.56291, -75.55897, -75.55897],
        "ciudad": ["Medellin"] * 3,
    }
)


def servidor_simulado(llamadas):
    def fetcher(url):
        llamadas.append(url)
        q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
        horas = pd.date_range(q["start_date"], f"{q['end_date']} 23:00", freq="h")
        n = len(horas)
        lats = [float(x) for x in q["latitude"].split(",")]
        t = np.arange(n)
        respuestas = []
        for i, lat in enumerate(lats):
            if "models" in q:  # ERA5
                hourly = {"precipitation": list(np.round(np.where(t % 7 == i, 1.2, 0.0), 1))}
                units = {"precipitation": "mm"}
            else:
                hourly = {
                    "temperature_2m": list(20 + np.sin(t / 24)),
                    "relative_humidity_2m": [80.0] * n,
                    "dew_point_2m": [16.0] * n,
                    "cloud_cover": list((t * 7 % 100).astype(float)),
                    "wind_speed_10m": [2.0] * n,
                    "wind_direction_10m": [180.0] * n,
                    "pressure_msl": [1012.0] * n,
                    "precipitation": [0.0] * n,
                    "cape": [100.0] * n,
                }
                units = EXPECTED_FORECAST_UNITS
            hourly["time"] = [h.strftime("%Y-%m-%dT%H:%M") for h in horas]
            respuestas.append(
                {
                    "latitude": round(lat, 1),
                    "longitude": -75.5,
                    "hourly_units": dict(units, time="iso8601"),
                    "hourly": hourly,
                }
            )
        return json.dumps(respuestas).encode()

    return fetcher


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    raw = tmp_path / "data" / "raw"
    (raw / "siata").mkdir(parents=True)
    ESTACIONES.to_csv(raw / "siata" / "siata.csv", index=False)
    rutas = {
        "RAW_DATA_DIR": raw,
        "SIATA_RAW_CSV": raw / "siata" / "siata.csv",
        "RAW_MANIFEST": raw / "MANIFEST.json",
        "OPENMETEO_RAW_DIR": raw / "openmeteo",
        "EXTERNAL_DATA_DIR": tmp_path / "data" / "external",
        "STATIONS_CSV": tmp_path / "data" / "external" / "stations.csv",
        "FORECAST_INTERIM": tmp_path / "data" / "interim" / "f.parquet",
        "REFERENCE_INTERIM": tmp_path / "data" / "interim" / "r.parquet",
        "DATASET_PROCESSED": tmp_path / "data" / "processed" / "d.parquet",
        "DATA_QUALITY_REPORT": tmp_path / "reports" / "dq.json",
    }
    for k, v in rutas.items():
        monkeypatch.setattr(config, k, v)
    return rutas


def test_pipeline_completo_idempotente_y_determinista(entorno):
    llamadas = []
    r1 = dataset.run(fetcher=servidor_simulado(llamadas))
    assert len(llamadas) == 8
    df = pd.read_parquet(entorno["DATASET_PROCESSED"])
    assert len(df) == 2 * 35064
    assert df["station_id"].unique().tolist() == [59, 68]
    assert str(df["time_utc"].dtype) == "datetime64[us, UTC]"
    assert df["rain"].sum() == (df["precipitation_ref"] >= config.LABEL_THRESHOLD_MM).sum() > 0
    assert r1["ok"] and r1["downloads"]["forecast"] == {"new": 4, "cached": 0}

    r2 = dataset.run(fetcher=servidor_simulado(llamadas))
    assert len(llamadas) == 8  # 0 descargas nuevas
    assert r2["downloads"]["era5"] == {"new": 0, "cached": 4}
    huella = r1["stages"]["rain_hourly"]["content_fingerprint"]
    assert huella == r2["stages"]["rain_hourly"]["content_fingerprint"]

    reporte = json.loads(entorno["DATA_QUALITY_REPORT"].read_text(encoding="utf-8"))
    assert reporte["ok"] and set(reporte["stages"]) == {"openmeteo_forecast", "openmeteo_era5", "rain_hourly"}
    manifiesto = json.loads(entorno["RAW_MANIFEST"].read_text(encoding="utf-8"))
    assert {e["source"] for e in manifiesto.values()} == {"openmeteo-forecast", "openmeteo-era5", "siata"}


def test_etapa_invalida_no_promueve_y_queda_en_el_reporte(entorno, monkeypatch):
    original = dataset.parse_raw

    def humedad_imposible(paths, ids, source):
        df = original(paths, ids, source)
        if source == "forecast":
            df.loc[0, "relative_humidity_2m"] = 150.0
        return df

    monkeypatch.setattr(dataset, "parse_raw", humedad_imposible)
    with pytest.raises(DataContractError, match="range:relative_humidity_2m"):
        dataset.run(fetcher=servidor_simulado([]))
    assert not entorno["FORECAST_INTERIM"].exists()
    assert not entorno["DATASET_PROCESSED"].exists()
    reporte = json.loads(entorno["DATA_QUALITY_REPORT"].read_text(encoding="utf-8"))
    assert reporte["ok"] is False and reporte["stages"]["openmeteo_forecast"]["ok"] is False


def test_filas_incompletas_se_descartan_sin_imputar():
    t = pd.date_range("2022-01-01", periods=3, freq="h", tz="UTC")
    base = {"station_id": np.int64(59), "time_utc": t}
    feats = {c: [1.0, np.nan, 1.0] if c == "cape" else [1.0] * 3 for c in config.FORECAST_VARIABLES}
    forecast = pd.DataFrame(base | feats)
    reference = pd.DataFrame(base | {"precipitation_ref": [0.0, 2.0, 0.6], "era5_cell": "6.25,-75.5"})
    stations = pd.DataFrame({"station_id": [59], "latitude": [6.2], "longitude": [-75.5]})
    df, resumen = dataset.build_processed(forecast, reference, stations, threshold_mm=0.5)
    assert len(df) == 2 and resumen["dropped_incomplete_rows"] == 1
    assert df["rain"].tolist() == [False, True]


def test_huella_no_depende_del_orden_de_filas():
    t = pd.date_range("2022-01-01", periods=3, freq="h", tz="UTC")
    df = pd.DataFrame({"station_id": np.int64(1), "time_utc": t, "x": [1.0, 2.0, 3.0]})
    assert dataset.content_fingerprint(df) == dataset.content_fingerprint(df.iloc[::-1])
    assert dataset.content_fingerprint(df) != dataset.content_fingerprint(df.assign(x=[1.0, 2.0, 4.0]))
