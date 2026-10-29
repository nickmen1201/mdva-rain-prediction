import json
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from mdva import openmeteo
from mdva.data_contract import EXPECTED_FORECAST_UNITS, DataContractError

LATS, LONS = (6.21394, 6.26925), (-75.55897, -75.56291)


def _respuesta(units=EXPECTED_FORECAST_UNITS, n=2):
    return json.dumps(
        [{"latitude": 6.2, "longitude": -75.5, "hourly_units": dict(units, time="iso8601"), "hourly": {}}] * n
    ).encode()


def test_url_pide_unidades_explicitas_y_utc():
    q = parse_qs(urlparse(openmeteo.build_url("forecast", LATS, LONS, 2023)).query)
    assert q["timezone"] == ["GMT"]
    assert q["wind_speed_unit"] == ["ms"]
    assert q["temperature_unit"] == ["celsius"]
    assert q["precipitation_unit"] == ["mm"]
    assert q["start_date"] == ["2023-01-01"] and q["end_date"] == ["2023-12-31"]
    assert q["latitude"] == ["6.21394,6.26925"]
    assert q["hourly"][0].split(",") == list(openmeteo.config.FORECAST_VARIABLES)


def test_url_era5_pide_el_modelo_era5():
    q = parse_qs(urlparse(openmeteo.build_url("era5", LATS, LONS, 2022)).query)
    assert q["models"] == ["era5"] and q["hourly"] == ["precipitation"]
    assert urlparse(openmeteo.build_url("era5", LATS, LONS, 2022)).netloc == "archive-api.open-meteo.com"


class _Resp:
    def __init__(self, status, content=b"{}", headers=None):
        self.status_code, self.content, self.headers = status, content, headers or {}

    def raise_for_status(self):
        raise requests.HTTPError(f"HTTP {self.status_code}")


def test_fetch_reintenta_con_espera_exponencial(monkeypatch):
    respuestas = iter([_Resp(429), _Resp(503), _Resp(200, b"ok")])
    monkeypatch.setattr(openmeteo.requests, "get", lambda url, timeout: next(respuestas))
    esperas = []
    assert openmeteo.fetch("u", sleep=esperas.append) == b"ok"
    assert esperas == [15.0, 30.0]


def test_fetch_respeta_retry_after(monkeypatch):
    respuestas = iter([_Resp(429, headers={"Retry-After": "42"}), _Resp(200, b"ok")])
    monkeypatch.setattr(openmeteo.requests, "get", lambda url, timeout: next(respuestas))
    esperas = []
    openmeteo.fetch("u", sleep=esperas.append)
    assert esperas == [42.0]


def test_fetch_falla_tras_agotar_reintentos(monkeypatch):
    monkeypatch.setattr(openmeteo.requests, "get", lambda url, timeout: _Resp(429))
    with pytest.raises(RuntimeError, match="3 intentos"):
        openmeteo.fetch("u", retries=3, sleep=lambda s: None)


def test_fetch_no_reintenta_errores_del_cliente(monkeypatch):
    monkeypatch.setattr(openmeteo.requests, "get", lambda url, timeout: _Resp(400))
    with pytest.raises(requests.HTTPError):
        openmeteo.fetch("u", sleep=lambda s: None)


def test_descarga_es_idempotente(tmp_path):
    manifest = openmeteo.Manifest(tmp_path / "MANIFEST.json", tmp_path)
    llamadas = []

    def fetcher(url):
        llamadas.append(url)
        return _respuesta()

    ruta, nuevo = openmeteo.download_year("forecast", 2022, LATS, LONS, manifest, tmp_path, fetcher=fetcher)
    assert nuevo and ruta.exists()
    manifest2 = openmeteo.Manifest(tmp_path / "MANIFEST.json", tmp_path)
    _, nuevo2 = openmeteo.download_year("forecast", 2022, LATS, LONS, manifest2, tmp_path, fetcher=fetcher)
    assert not nuevo2 and len(llamadas) == 1
    entrada = manifest2.entries["forecast/2022.json"]
    assert entrada["source"] == "openmeteo-forecast" and len(entrada["sha256"]) == 64


def test_archivo_alterado_se_vuelve_a_descargar(tmp_path):
    manifest = openmeteo.Manifest(tmp_path / "MANIFEST.json", tmp_path)
    ruta, _ = openmeteo.download_year("forecast", 2022, LATS, LONS, manifest, tmp_path, fetcher=lambda u: _respuesta())
    ruta.write_bytes(b"corrupto")
    _, nuevo = openmeteo.download_year("forecast", 2022, LATS, LONS, manifest, tmp_path, fetcher=lambda u: _respuesta())
    assert nuevo


def test_unidades_equivocadas_no_se_escriben(tmp_path):
    manifest = openmeteo.Manifest(tmp_path / "MANIFEST.json", tmp_path)
    malas = dict(EXPECTED_FORECAST_UNITS, wind_speed_10m="km/h")
    with pytest.raises(DataContractError, match="units"):
        openmeteo.download_year("forecast", 2022, LATS, LONS, manifest, tmp_path, fetcher=lambda u: _respuesta(malas))
    assert not (tmp_path / "forecast" / "2022.json").exists()
    assert manifest.entries == {}


def test_numero_de_ubicaciones_incorrecto_falla(tmp_path):
    manifest = openmeteo.Manifest(tmp_path / "MANIFEST.json", tmp_path)
    with pytest.raises(RuntimeError, match="1 ubicaciones recibidas, 2 pedidas"):
        openmeteo.download_year("forecast", 2022, LATS, LONS, manifest, tmp_path, fetcher=lambda u: _respuesta(n=1))


def test_escritura_atomica_no_deja_temporales(tmp_path):
    openmeteo.write_atomic(tmp_path / "x.json", b"{}")
    assert [p.name for p in tmp_path.iterdir()] == ["x.json"]
