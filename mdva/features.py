"""Única definición de features para entrenamiento e inferencia (spec 004).

Entradas crudas: instante UTC objetivo + 9 variables pronosticadas de Open-Meteo (mismas
unidades y rangos que el contrato de datos `rain_hourly`). Salida: 13 features en orden
fijo y versionado. Ningún otro componente del sistema recalcula features.

Contrato: specs/004-feature-contract/contracts/features.v1.md · Documentación: docs/features.md
"""

from __future__ import annotations

from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from mdva import config
from mdva.data_contract import DATASET_CONTRACT

FEATURE_CONTRACT_VERSION = "1.0.0"
LOCAL_TZ = ZoneInfo("America/Bogota")

TIME_INPUT = "time_utc"
RAW_INPUTS = {c.name: c for c in DATASET_CONTRACT.columns if c.name in config.FORECAST_VARIABLES}

FEATURES = (
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
    return f[list(FEATURES)].astype("float64")


def _is_datetime(s: pd.Series) -> bool:
    return pd.api.types.is_datetime64_any_dtype(s)
