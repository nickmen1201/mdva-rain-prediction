"""RainSignalClient: una sola señal de lluvia, sin valores inventados y con caché por clave (spec 009)."""

from datetime import UTC, datetime

import pytest
import requests
from infrastructure.rain_signal import VARIABLES, RainSignal, RainSignalClient, TTLCache

AHORA = datetime(2026, 10, 31, 15, 23, tzinfo=UTC)


def _open_meteo(units=None):
    horas = [f"2026-10-31T{h:02d}:00" for h in range(24)]
    valores = {
        "temperature_2m": 21.0,
        "relative_humidity_2m": 80.0,
        "dew_point_2m": 17.4,
        "cloud_cover": 90.0,
        "wind_speed_10m": 2.5,
        "wind_direction_10m": 200.0,
        "pressure_msl": 1012.0,
        "precipitation": 0.3,
        "cape": 450.0,
    }
    hourly = {"time": horas, **{k: [v + h for h in range(24)] for k, v in valores.items()}}
    return {"hourly_units": units or dict(VARIABLES), "hourly": hourly}


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._body


class _Session:
    """Simula Open-Meteo (GET) y el ML API (POST) y registra las llamadas."""

    def __init__(self, om=None, ml=None, om_error=None, ml_error=None):
        self.om = om if om is not None else _Resp(200, _open_meteo())
        self.ml = (
            ml if ml is not None else _Resp(200, {"probability": 0.75, "alert_level": "ROJO", "model_version": "1.0.0"})
        )
        self.om_error, self.ml_error = om_error, ml_error
        self.gets, self.posts = [], []

    def get(self, url, params=None, timeout=None):
        self.gets.append(params)
        if self.om_error:
            raise self.om_error
        return self.om

    def post(self, url, json=None, timeout=None):
        self.posts.append((url, json))
        if self.ml_error:
            raise self.ml_error
        return self.ml


class _Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _client(session, clock=None):
    return RainSignalClient("http://ml:8081/", session=session, clock=clock or _Clock(), now_utc=lambda: AHORA)


def test_senal_del_modelo_v2_con_la_hora_utc_en_curso():
    s = _Session()
    sig = _client(s).signal(6.2502, -75.5684)

    assert sig == RainSignal(True, 0.75, "ROJO", "1.0.0", "2026-10-31T15:00:00Z")
    assert sig.time_factor == 1.35
    params = s.gets[0]
    assert params["wind_speed_unit"] == "ms" and params["timezone"] == "GMT"
    assert params["temperature_unit"] == "celsius" and params["precipitation_unit"] == "mm"
    url, record = s.posts[0]
    assert url == "http://ml:8081/v2/predict"
    assert record["time_utc"] == "2026-10-31T15:00:00Z"
    assert record["temperature_2m"] == 21.0 + 15  # valor de la hora 15
    assert params["past_days"] == 1 and params["forecast_days"] == 2
    # Contrato de features 1.1.0: ventana del mismo pronóstico y ubicación
    assert record["precipitation_prev2"] == 0.3 + 13 and record["precipitation_next1"] == 0.3 + 16
    assert record["cloud_cover_prev1"] == 90.0 + 14 and record["cape_next1"] == 450.0 + 16
    assert record["latitude"] == 6.2502 and record["longitude"] == -75.5684
    assert len(record) == 1 + 9 + 8 + 2


@pytest.mark.parametrize(
    "session",
    [
        _Session(om_error=requests.ConnectionError("caído")),
        _Session(om=_Resp(503, {})),
        _Session(om=_Resp(200, _open_meteo(units={**VARIABLES, "wind_speed_10m": "km/h"}))),
        _Session(ml_error=requests.Timeout("lento")),
        _Session(ml=_Resp(422, {"title": "fuera de rango"})),
        _Session(ml=_Resp(200, {"detail": "sin probabilidad"})),
    ],
    ids=["om-caido", "om-503", "om-km/h", "ml-timeout", "ml-422", "ml-respuesta-invalida"],
)
def test_fallos_declaran_no_disponible_sin_inventar(session):
    sig = _client(session).signal(6.25, -75.57)

    assert sig == RainSignal.unavailable()
    assert sig.probability is None and sig.alert_level is None
    assert sig.time_factor == 1.0


def test_sin_hora_vecina_para_la_ventana_no_se_rellena():
    om = _open_meteo()
    om["hourly"] = {k: v[:17] for k, v in om["hourly"].items()}  # termina a las 16:00: falta t+2
    assert _client(_Session(om=_Resp(200, om))).signal(6.25, -75.57).available is False


def test_hora_ausente_en_el_pronostico_no_se_rellena():
    om = _open_meteo()
    om["hourly"]["time"] = om["hourly"]["time"][:10]
    assert _client(_Session(om=_Resp(200, om))).signal(6.25, -75.57).available is False


def test_cache_por_clave_vence_de_forma_independiente():
    s, clock = _Session(), _Clock()
    client = _client(s, clock)

    client.signal(6.2502, -75.5684)  # A en t=0
    clock.t = 240
    client.signal(6.2088, -75.5672)  # B en t=4 min
    client.signal(6.2549, -75.5711)  # A otra vez (misma celda de 2 decimales): caché
    assert len(s.posts) == 2

    clock.t = 360  # t=6 min: A vencida, B vigente
    client.signal(6.2502, -75.5684)
    client.signal(6.2088, -75.5672)
    assert len(s.posts) == 3


def test_los_fallos_no_se_cachean():
    s = _Session(ml_error=requests.ConnectionError("caído"))
    client = _client(s)
    assert client.signal(6.25, -75.57).available is False

    s.ml_error = None
    assert client.signal(6.25, -75.57).available is True


def test_ttlcache_basico():
    clock = _Clock()
    cache = TTLCache(10, clock)
    cache.put("k", 1)
    clock.t = 9.9
    assert cache.get("k") == 1
    clock.t = 10
    assert cache.get("k") is None
    assert cache.get("otra") is None


@pytest.mark.parametrize(("nivel", "factor"), [("VERDE", 1.0), ("AMARILLO", 1.2), ("ROJO", 1.35)])
def test_factor_rf10(nivel, factor):
    assert RainSignal(True, 0.5, nivel).time_factor == factor
