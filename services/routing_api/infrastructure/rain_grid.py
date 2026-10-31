"""Grilla espacial de probabilidad de lluvia para la ruta `dryest` (spec 010, charter R-26).

Una malla regular 5 × 5 sobre la caja del viaje: una consulta multi-ubicación a Open-Meteo y una
llamada por lotes al ML API (mismo modelo, fuente y variables que el resto del sistema). La
probabilidad en cualquier punto se obtiene por interpolación bilineal; fuera de la malla, el borde.
Si falta cualquier punto, la grilla no está disponible: nada se rellena (constitución VII).
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
import requests
from infrastructure.rain_signal import (
    OPEN_METEO_PARAMS,
    OPEN_METEO_URL,
    TTL_SECONDS,
    TTLCache,
    current_hour,
    model_record,
)

log = logging.getLogger(__name__)

N = 5
MIN_SPAN_DEG = 0.02
MARGIN_DEG = 0.01


@dataclass(frozen=True)
class RainGrid:
    """Probabilidades `p[i, j]` en `lats[i]` (ascendente) × `lons[j]` (ascendente)."""

    lats: np.ndarray
    lons: np.ndarray
    p: np.ndarray
    model_version: str | None = None
    time_utc: str | None = None

    @property
    def max_probability(self) -> float:
        return float(self.p.max())

    def at(self, lat: float, lon: float) -> float:
        """Interpolación bilineal; fuera de la malla se usa el borde más cercano."""
        lat = min(max(lat, self.lats[0]), self.lats[-1])
        lon = min(max(lon, self.lons[0]), self.lons[-1])
        i = int(np.clip(np.searchsorted(self.lats, lat) - 1, 0, len(self.lats) - 2))
        j = int(np.clip(np.searchsorted(self.lons, lon) - 1, 0, len(self.lons) - 2))
        ty = (lat - self.lats[i]) / (self.lats[i + 1] - self.lats[i])
        tx = (lon - self.lons[j]) / (self.lons[j + 1] - self.lons[j])
        p = self.p
        arriba = p[i, j] * (1 - tx) + p[i, j + 1] * tx
        abajo = p[i + 1, j] * (1 - tx) + p[i + 1, j + 1] * tx
        return float(arriba * (1 - ty) + abajo * ty)


def grid_axes(points: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """Ejes de la malla sobre la caja de los puntos (lat, lon), con margen y lado mínimo."""
    lats = [p[0] for p in points]
    lons = [p[1] for p in points]

    def eje(lo, hi):
        lo, hi = lo - MARGIN_DEG, hi + MARGIN_DEG
        if hi - lo < MIN_SPAN_DEG:
            c = (lo + hi) / 2
            lo, hi = c - MIN_SPAN_DEG / 2, c + MIN_SPAN_DEG / 2
        return np.round(np.linspace(lo, hi, N), 4)

    return eje(min(lats), max(lats)), eje(min(lons), max(lons))


class RainGridClient:
    def __init__(
        self,
        ml_url: str,
        session: requests.Session | None = None,
        clock: Callable[[], float] = time.monotonic,
        now_utc: Callable[[], datetime] = lambda: datetime.now(UTC),
        open_meteo_url: str = OPEN_METEO_URL,
        timeout_s: float = 10.0,
    ):
        self._ml_url = ml_url.rstrip("/")
        self._session = session or requests.Session()
        self._cache = TTLCache(TTL_SECONDS, clock)
        self._now_utc = now_utc
        self._open_meteo_url = open_meteo_url
        self._timeout = timeout_s

    def grid(self, points: list[tuple[float, float]]) -> RainGrid | None:
        lats, lons = grid_axes(points)
        key = f"{lats[0]:.2f},{lats[-1]:.2f},{lons[0]:.2f},{lons[-1]:.2f}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        try:
            grid = self._fetch(lats, lons)
        except (requests.RequestException, KeyError, ValueError, TypeError, IndexError) as e:
            log.warning("Grilla de lluvia no disponible para %s: %s", key, e)
            return None
        self._cache.put(key, grid)
        return grid

    def _fetch(self, lats: np.ndarray, lons: np.ndarray) -> RainGrid:
        malla = [(float(la), float(lo)) for la in lats for lo in lons]  # fila = latitud
        params = {
            "latitude": ",".join(f"{la}" for la, _ in malla),
            "longitude": ",".join(f"{lo}" for _, lo in malla),
            **OPEN_METEO_PARAMS,
        }
        r = self._session.get(self._open_meteo_url, params=params, timeout=self._timeout)
        r.raise_for_status()
        ubicaciones = r.json()
        if not isinstance(ubicaciones, list) or len(ubicaciones) != len(malla):
            n = len(ubicaciones) if isinstance(ubicaciones, list) else 1
            raise ValueError(f"Open-Meteo devolvió {n} ubicaciones de {len(malla)}")

        hora = current_hour(self._now_utc())
        records = [model_record(u, hora, la, lo) for u, (la, lo) in zip(ubicaciones, malla, strict=True)]

        r = self._session.post(f"{self._ml_url}/v2/predict/batch", json={"records": records}, timeout=self._timeout)
        r.raise_for_status()
        body = r.json()
        probs = [float(p["probability"]) for p in body["predictions"]]
        if len(probs) != len(malla):
            raise ValueError(f"El ML API devolvió {len(probs)} predicciones de {len(malla)}")
        return RainGrid(
            lats=lats,
            lons=lons,
            p=np.asarray(probs).reshape(N, N),
            model_version=body.get("model_version"),
            time_utc=f"{hora}:00Z",
        )
