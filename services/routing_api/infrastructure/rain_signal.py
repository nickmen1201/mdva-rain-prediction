"""Única señal de lluvia del routing service (spec 009, charter R-25, R-28, R-29).

Pide a Open-Meteo las 9 variables del contrato de features para la hora UTC en curso (las mismas
del entrenamiento y del Backend, con unidades explícitas y verificadas) y llama a `POST /v2/predict`
del ML API, que calcula las features con `mdva`. Contrato de features 1.1.0 (spec 012): el registro
lleva además la ventana del mismo pronóstico (t−2…t+2) y la ubicación del punto. Si algo falla, la
señal queda *no disponible*: nunca se inventan valores (constitución VII).
"""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Callable

import requests

log = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Variables crudas del contrato de features v1.0.0 (docs/features.md) y su unidad declarada
VARIABLES = {
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "dew_point_2m": "°C",
    "cloud_cover": "%",
    "wind_speed_10m": "m/s",
    "wind_direction_10m": "°",
    "pressure_msl": "hPa",
    "precipitation": "mm",
    "cape": "J/kg",
}

# Ventana del pronóstico del contrato de features 1.1.0: variable → desplazamientos en horas
WINDOW_OFFSETS = {"precipitation": (-2, -1, 1, 2), "cloud_cover": (-1, 1), "cape": (-1, 1)}

# Parámetros comunes de las consultas a Open-Meteo (un día atrás para la ventana de la hora en curso)
OPEN_METEO_PARAMS = {
    "hourly": ",".join(VARIABLES),
    "past_days": 1,
    "forecast_days": 2,  # la hora en curso necesita t+2 aunque sea la última del día
    "timezone": "GMT",
    "wind_speed_unit": "ms",
    "temperature_unit": "celsius",
    "precipitation_unit": "mm",
}


def current_hour(now: datetime) -> str:
    return now.replace(minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M")


def model_record(location: dict, hora: str, lat: float, lon: float) -> dict:
    """Registro del contrato 1.1.0 para `hora` desde una ubicación de Open-Meteo (unidades verificadas).

    Lanza ValueError si falta la hora, alguna vecina de la ventana o algún valor: no se rellena nada.
    """
    units = location["hourly_units"]
    for var, unit in VARIABLES.items():
        if units.get(var) != unit:
            raise ValueError(f"Open-Meteo declaró {var}={units.get(var)!r}, se esperaba {unit!r}")
    hourly = location["hourly"]
    tiempos = hourly["time"]
    try:
        i = tiempos.index(hora)
    except ValueError:
        raise ValueError(f"La hora UTC {hora} no está en el pronóstico") from None

    def valor(var, j):
        if not 0 <= j < len(tiempos):
            raise ValueError(f"Falta la hora vecina {j - i:+d} h de {hora} para la ventana")
        v = hourly[var][j]
        if v is None:
            raise ValueError(f"Open-Meteo no trae {var} para {tiempos[j]}")
        return v

    record = {"time_utc": f"{hora}:00Z", **{var: valor(var, i) for var in VARIABLES}}
    for var, offsets in WINDOW_OFFSETS.items():
        for k in offsets:
            record[f"{var}_{'prev' if k < 0 else 'next'}{abs(k)}"] = valor(var, i + k)
    record["latitude"] = lat
    record["longitude"] = lon
    return record


# Factor de tiempo por nivel de alerta (charter RF-10)
FACTOR_POR_NIVEL = {"VERDE": 1.00, "AMARILLO": 1.20, "ROJO": 1.35}

TTL_SECONDS = 300


@dataclass(frozen=True)
class RainSignal:
    available: bool
    probability: float | None = None
    alert_level: str | None = None
    model_version: str | None = None
    time_utc: str | None = None

    @staticmethod
    def unavailable() -> "RainSignal":
        return RainSignal(available=False)

    @property
    def time_factor(self) -> float:
        """Factor RF-10 sobre el tiempo de viaje; 1.0 si no hay señal (sin penalización)."""
        return FACTOR_POR_NIVEL.get(self.alert_level, 1.0) if self.available else 1.0


class TTLCache:
    """Caché con instante por clave (corrige H-12: una sola marca de tiempo global)."""

    def __init__(self, ttl_seconds: float, clock: Callable[[], float] = time.monotonic):
        self._ttl = ttl_seconds
        self._clock = clock
        self._data: dict[str, tuple[object, float]] = {}

    def get(self, key: str):
        hit = self._data.get(key)
        if hit is None:
            return None
        value, stored_at = hit
        if self._clock() - stored_at >= self._ttl:
            del self._data[key]
            return None
        return value

    def put(self, key: str, value) -> None:
        self._data[key] = (value, self._clock())


class RainSignalClient:
    def __init__(
        self,
        ml_url: str,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        now_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        open_meteo_url: str = OPEN_METEO_URL,
        timeout_s: float = 5.0,
    ):
        self._ml_url = ml_url.rstrip("/")
        self._session = session or requests.Session()
        self._cache = TTLCache(TTL_SECONDS, clock)
        self._now_utc = now_utc
        self._open_meteo_url = open_meteo_url
        self._timeout = timeout_s

    def signal(self, lat: float, lon: float) -> RainSignal:
        key = f"{lat:.2f},{lon:.2f}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            record = self._current_inputs(lat, lon)
            r = self._session.post(f"{self._ml_url}/v2/predict", json=record, timeout=self._timeout)
            r.raise_for_status()
            body = r.json()
            result = RainSignal(
                available=True,
                probability=float(body["probability"]),
                alert_level=body["alert_level"],
                model_version=body.get("model_version"),
                time_utc=record["time_utc"],
            )
        except (requests.RequestException, KeyError, ValueError, TypeError) as e:
            # Las señales fallidas no se cachean: el siguiente pedido vuelve a intentar
            log.warning("Señal de lluvia no disponible para %s: %s", key, e)
            return RainSignal.unavailable()
        self._cache.put(key, result)
        return result

    def _current_inputs(self, lat: float, lon: float) -> dict:
        params = {"latitude": lat, "longitude": lon, **OPEN_METEO_PARAMS}
        r = self._session.get(self._open_meteo_url, params=params, timeout=self._timeout)
        r.raise_for_status()
        return model_record(r.json(), current_hour(self._now_utc()), lat, lon)
