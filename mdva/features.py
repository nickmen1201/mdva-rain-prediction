"""Única definición de features para entrenamiento e inferencia (specs 004 y 012).

Entradas crudas (contrato 1.1.0):
- instante UTC objetivo + 9 variables pronosticadas de Open-Meteo para esa hora;
- **ventana del pronóstico**: precipitación de las horas t−2, t−1, t+1, t+2 y nubosidad y CAPE de
  t−1 y t+1, del **mismo** pronóstico horario (en producción vienen en la misma respuesta de
  Open-Meteo; en el dataset se arman con `forecast_window_inputs`);
- **ubicación**: latitud y longitud del punto.

Salida: 24 features en orden fijo y versionado. Ningún otro componente recalcula features; los
servicios envían variables crudas con las unidades del contrato de datos `rain_hourly`.

Contratos: specs/004-feature-contract/contracts/features.v1.md (1.0.0) y
specs/012-ml-depth/contracts/features.v1.1.md (1.1.0) · Documentación: docs/features.md
"""

from __future__ import annotations

import dataclasses
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from mdva import config
from mdva.data_contract import DATASET_CONTRACT

FEATURE_CONTRACT_VERSION = "1.1.0"
LOCAL_TZ = ZoneInfo("America/Bogota")

TIME_INPUT = "time_utc"
_COLUMNAS = {c.name: c for c in DATASET_CONTRACT.columns}
FORECAST_INPUTS = {nombre: _COLUMNAS[nombre] for nombre in config.FORECAST_VARIABLES}

# Ventana del pronóstico: variable → desplazamientos en horas respecto de la hora objetivo
WINDOW_OFFSETS = {"precipitation": (-2, -1, 1, 2), "cloud_cover": (-1, 1), "cape": (-1, 1)}


def window_input_name(variable: str, offset: int) -> str:
    return f"{variable}_prev{-offset}" if offset < 0 else f"{variable}_next{offset}"


WINDOW_INPUTS = {
    window_input_name(var, k): dataclasses.replace(_COLUMNAS[var], name=window_input_name(var, k))
    for var, offsets in WINDOW_OFFSETS.items()
    for k in offsets
}
LOCATION_INPUTS = {nombre: _COLUMNAS[nombre] for nombre in ("latitude", "longitude")}
RAW_INPUTS = {**FORECAST_INPUTS, **WINDOW_INPUTS, **LOCATION_INPUTS}

# Contrato 1.0.0: las 13 primeras features (las usa la versión 1.0.0 del modelo)
BASE_FEATURES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_depression",
    "cloud_cover",
    "wind_u",
    "wind_v",
    "pressure_msl",
    "precipitation_log1p",
    "cape_log1p",
    "hour_sin",
    "hour_cos",
    "month_sin",
    "month_cos",
)
WINDOW_FEATURES = (
    "precipitation_prev2_log1p",
    "precipitation_prev1_log1p",
    "precipitation_next1_log1p",
    "precipitation_next2_log1p",
    "cloud_cover_prev1",
    "cloud_cover_next1",
    "cape_prev1_log1p",
    "cape_next1_log1p",
    "precipitation_5h_log1p",
)
LOCATION_FEATURES = ("latitude", "longitude")
FEATURES = BASE_FEATURES + WINDOW_FEATURES + LOCATION_FEATURES


class FeatureInputError(ValueError):
    """Entradas que no cumplen el contrato; `problems` lista (campo, regla)."""

    def __init__(self, problems: list[tuple[str, str]]):
        self.problems = problems
        super().__init__("; ".join(f"{campo}: {regla}" for campo, regla in problems))


def validate_inputs(raw: pd.DataFrame | list[dict]) -> pd.DataFrame:
    """Valida las entradas crudas y devuelve un DataFrame con `time_utc` en UTC y variables en float."""
    df = pd.DataFrame(raw) if not isinstance(raw, pd.DataFrame) else raw
    problems: list[tuple[str, str]] = []

    for campo in (TIME_INPUT, *RAW_INPUTS):
        if campo not in df.columns:
            problems.append((campo, "campo faltante"))
    if problems:
        raise FeatureInputError(problems)

    out = pd.DataFrame(index=df.index)
    tiempos = df[TIME_INPUT]
    if tiempos.isna().any():
        problems.append((TIME_INPUT, "nulo"))
    else:
        try:
            parsed = pd.to_datetime(tiempos, format="ISO8601") if not _is_datetime(tiempos) else tiempos
        except (ValueError, TypeError):
            problems.append((TIME_INPUT, "no es un instante ISO 8601"))
        else:
            if getattr(parsed.dt, "tz", None) is None:
                problems.append((TIME_INPUT, "instante sin zona horaria"))
            else:
                out[TIME_INPUT] = parsed.dt.tz_convert("UTC")

    for campo, col in RAW_INPUTS.items():
        valores = pd.to_numeric(df[campo], errors="coerce").astype("float64")
        if valores.isna().any():
            problems.append((campo, "nulo o no numérico"))
            continue
        fuera = (valores < col.min) | (valores > col.max)
        if fuera.any():
            problems.append((campo, f"fuera de rango [{col.min}, {col.max}] {col.unit}: {valores[fuera].iloc[0]}"))
            continue
        out[campo] = valores

    if problems:
        raise FeatureInputError(problems)
    return out


def build_features(raw: pd.DataFrame | list[dict]) -> pd.DataFrame:
    """Valida y transforma entradas crudas en la matriz de features (columnas = FEATURES)."""
    x = validate_inputs(raw)
    local = x[TIME_INPUT].dt.tz_convert(LOCAL_TZ)
    hora = local.dt.hour.to_numpy()
    mes = local.dt.month.to_numpy()
    direccion = np.deg2rad(x["wind_direction_10m"].to_numpy())
    velocidad = x["wind_speed_10m"].to_numpy()

    f = pd.DataFrame(index=x.index)
    f["temperature_2m"] = x["temperature_2m"]
    f["relative_humidity_2m"] = x["relative_humidity_2m"]
    f["dew_point_depression"] = x["temperature_2m"] - x["dew_point_2m"]
    f["cloud_cover"] = x["cloud_cover"]
    # Convención meteorológica: la dirección indica de dónde viene el viento
    f["wind_u"] = -velocidad * np.sin(direccion)
    f["wind_v"] = -velocidad * np.cos(direccion)
    f["pressure_msl"] = x["pressure_msl"]
    f["precipitation_log1p"] = np.log1p(x["precipitation"])
    f["cape_log1p"] = np.log1p(x["cape"])
    f["hour_sin"] = np.sin(2 * np.pi * hora / 24)
    f["hour_cos"] = np.cos(2 * np.pi * hora / 24)
    f["month_sin"] = np.sin(2 * np.pi * (mes - 1) / 12)
    f["month_cos"] = np.cos(2 * np.pi * (mes - 1) / 12)

    # Ventana del pronóstico (contrato 1.1.0)
    for var, offsets in WINDOW_OFFSETS.items():
        for k in offsets:
            col = window_input_name(var, k)
            f[col if var == "cloud_cover" else f"{col}_log1p"] = x[col] if var == "cloud_cover" else np.log1p(x[col])
    lluvia_5h = x["precipitation"] + sum(
        x[window_input_name("precipitation", k)] for k in WINDOW_OFFSETS["precipitation"]
    )
    f["precipitation_5h_log1p"] = np.log1p(lluvia_5h)

    # Ubicación
    f["latitude"] = x["latitude"]
    f["longitude"] = x["longitude"]
    return f[list(FEATURES)].astype("float64")


def forecast_window_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """Entradas de la ventana desde la serie horaria de cada estación (solo para armar el dataset).

    Toma vecinos contiguos de la misma estación; si la hora vecina no existe (borde o hueco de la
    serie), queda NaN y la fila no pasa `validate_inputs` (no se rellena). En producción los vecinos
    vienen de la misma respuesta del pronóstico.
    """
    orden = df.sort_values(["station_id", TIME_INPUT])
    g = orden.groupby("station_id", sort=False)
    out = pd.DataFrame(index=orden.index)
    for var, offsets in WINDOW_OFFSETS.items():
        for k in offsets:
            contiguo = (g[TIME_INPUT].shift(-k) - orden[TIME_INPUT]) == pd.Timedelta(hours=k)
            out[window_input_name(var, k)] = g[var].shift(-k).where(contiguo)
    return out.loc[df.index]


def _is_datetime(s: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(s)
