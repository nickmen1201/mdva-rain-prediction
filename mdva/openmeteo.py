"""Cliente de Open-Meteo para el dataset (spec 003, research R1–R3).

- URLs con unidades explícitas y zona UTC.
- Reintentos con espera exponencial ante límite de tasa (429) o errores 5xx.
- Unidades verificadas antes de escribir: un crudo con unidades equivocadas nunca queda en caché.
- Escritura atómica y manifiesto SHA-256 para que las descargas sean idempotentes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

import requests

from mdva import config
from mdva.data_contract import EXPECTED_FORECAST_UNITS, EXPECTED_REFERENCE_UNITS, validate_units

log = logging.getLogger(__name__)

FORECAST_URL = "https://historical-forecast-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

SOURCES = {
    "forecast": {
        "url": FORECAST_URL,
        "params": {"hourly": ",".join(config.FORECAST_VARIABLES)},
        "units": EXPECTED_FORECAST_UNITS,
    },
    "era5": {
        "url": ARCHIVE_URL,
        "params": {"hourly": "precipitation", "models": "era5"},
        "units": EXPECTED_REFERENCE_UNITS,
    },
}

RETRY_STATUS = {429, 500, 502, 503, 504}


def build_url(source: str, latitudes: Sequence[float], longitudes: Sequence[float], year: int) -> str:
    spec = SOURCES[source]
    params = {
        "latitude": ",".join(f"{x:.5f}" for x in latitudes),
        "longitude": ",".join(f"{x:.5f}" for x in longitudes),
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        **spec["params"],
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
        "precipitation_unit": "mm",
        "timezone": "GMT",
    }
    return f"{spec['url']}?{urlencode(params, safe=',')}"


def fetch(
    url: str, *, retries: int = 5, base_delay: float = 15.0, sleep: Callable[[float], None] = time.sleep
) -> bytes:
    """Descarga con reintentos: respeta `Retry-After`; si no viene, espera 15, 30, 60 y 120 s.

    El límite gratuito de Open-Meteo es por minuto y pondera el tamaño de la petición
    (ubicaciones × variables × días), así que las esperas cortas no bastan.
    """
    for intento in range(1, retries + 1):
        retry_after = ""
        try:
            resp = requests.get(url, timeout=300)
        except requests.RequestException as e:
            motivo = type(e).__name__
        else:
            if resp.status_code == 200:
                return resp.content
            if resp.status_code not in RETRY_STATUS:
                resp.raise_for_status()
            motivo = f"HTTP {resp.status_code}"
            retry_after = resp.headers.get("Retry-After", "")
        if intento == retries:
            raise RuntimeError(f"Descarga fallida tras {retries} intentos ({motivo}): {url}")
        espera = float(retry_after) if retry_after.isdigit() else base_delay * 2 ** (intento - 1)
        log.warning("%s; reintento %d/%d en %.0f s", motivo, intento, retries - 1, espera)
        sleep(espera)
    raise AssertionError("inalcanzable")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def write_atomic(path: Path, data: bytes) -> None:
    """Escribe en un temporal del mismo directorio y renombra: nunca queda un archivo a medias."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


class Manifest:
    """Registro de archivos crudos: ruta relativa → fuente, URL, SHA-256 y fecha de descarga."""

    def __init__(self, path: Path, root: Path):
        self.path, self.root = path, root
        self.entries: dict[str, dict] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def _key(self, file: Path) -> str:
        return file.resolve().relative_to(self.root.resolve()).as_posix()

    def is_intact(self, file: Path) -> bool:
        entry = self.entries.get(self._key(file))
        return bool(entry) and file.exists() and sha256(file) == entry["sha256"]

    def record(self, file: Path, source: str, url: str | None) -> None:
        self.entries[self._key(file)] = {
            "source": source,
            "url": url,
            "sha256": sha256(file),
            "downloaded_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        write_atomic(self.path, json.dumps(self.entries, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def download_year(
    source: str,
    year: int,
    latitudes: Sequence[float],
    longitudes: Sequence[float],
    manifest: Manifest,
    raw_dir: Path,
    *,
    fetcher: Callable[[str], bytes] = fetch,
) -> tuple[Path, bool]:
    """Descarga (o reutiliza) el crudo de una fuente y un año. Devuelve (ruta, se_descargó)."""
    destino = raw_dir / source / f"{year}.json"
    if manifest.is_intact(destino):
        log.info("En caché: %s", destino.name)
        return destino, False

    url = build_url(source, latitudes, longitudes, year)
    data = fetcher(url)
    respuestas = json.loads(data)
    respuestas = respuestas if isinstance(respuestas, list) else [respuestas]
    if len(respuestas) != len(latitudes):
        raise RuntimeError(f"{source} {year}: {len(respuestas)} ubicaciones recibidas, {len(latitudes)} pedidas")
    for r in respuestas:
        validate_units(r["hourly_units"], SOURCES[source]["units"], f"{source}:{year}")

    write_atomic(destino, data)
    manifest.record(destino, f"openmeteo-{source}", url)
    log.info("Descargado: %s/%s (%.1f MB)", source, destino.name, len(data) / 1e6)
    return destino, True
