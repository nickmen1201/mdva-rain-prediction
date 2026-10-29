"""Splits temporales del dataset de lluvia (spec 005, data-model)."""

from __future__ import annotations

import pandas as pd

GAP = pd.Timedelta(hours=24)

TRAIN = (pd.Timestamp("2022-01-01", tz="UTC"), pd.Timestamp("2024-01-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-01-01", tz="UTC") + GAP, pd.Timestamp("2025-01-01", tz="UTC"))
TEST = (pd.Timestamp("2025-01-01", tz="UTC") + GAP, pd.Timestamp("2026-01-01", tz="UTC"))
# Reservado para la validación externa contra pluviómetros SIATA (spec 003): fuera del entrenamiento
EXTERNAL = (pd.Timestamp("2022-06-01", tz="UTC"), pd.Timestamp("2022-08-01", tz="UTC"))


def _entre(t: pd.Series, rango: tuple[pd.Timestamp, pd.Timestamp]) -> pd.Series:
    return (t >= rango[0]) & (t < rango[1])


def temporal_splits(time_utc: pd.Series) -> dict[str, pd.Series]:
    """Máscaras booleanas disjuntas: train, validation, test, external."""
    return {
        "train": _entre(time_utc, TRAIN) & ~_entre(time_utc, EXTERNAL),
        "validation": _entre(time_utc, VALIDATION),
        "test": _entre(time_utc, TEST),
        "external": _entre(time_utc, EXTERNAL),
    }


def describe(time_utc: pd.Series, y: pd.Series, masks: dict[str, pd.Series]) -> dict:
    out = {}
    for nombre, m in masks.items():
        t = time_utc[m]
        out[nombre] = {
            "start": t.min().isoformat() if len(t) else None,
            "end": t.max().isoformat() if len(t) else None,
            "rows": int(m.sum()),
            "rain_rate": round(float(y[m].mean()), 4) if m.any() else None,
        }
    out["train"]["excluded"] = [EXTERNAL[0].isoformat(), EXTERNAL[1].isoformat()]
    return out
