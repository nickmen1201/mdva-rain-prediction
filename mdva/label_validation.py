"""Validación externa de la etiqueta contra pluviómetros SIATA (spec 003, US3).

1. Agrega los datos minutales de SIATA a horas UTC (hora local UTC−5, research R5),
   con calidad 1, precipitación ≥ 0 y al menos 50 minutos válidos por hora.
2. Divide el periodo de SIATA en dos mitades disjuntas por tiempo.
3. Calibra el umbral de la referencia (y del pronóstico crudo) por igualación de
   frecuencias en la primera mitad.
4. Reporta la concordancia en la segunda mitad (por estación y total; ventanas de
   1, 3 y 6 h), el análisis de desfases −8…+8 h y el ciclo diurno de cada fuente.

Uso (desde la raíz del repo, después de `python -m mdva.dataset`):
    python -m mdva.label_validation
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import timedelta, timezone

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support

from mdva import config, openmeteo

log = logging.getLogger(__name__)

OBS_RAIN_MM = 0.1  # una hora es lluviosa en el pluviómetro si acumula ≥ 0.1 mm
MIN_VALID_MINUTES = 50
THRESHOLD_GRID_MM = (0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.5, 2.0)
WINDOWS_H = (1, 3, 6)
OFFSETS_H = range(-8, 9)
MIN_STATION_HOURS = 250  # horas de validación para reportar una estación por separado (SC-005)


def siata_hourly(siata_csv=None, utc_offset_hours: int = config.SIATA_UTC_OFFSET_HOURS) -> tuple[pd.DataFrame, dict]:
    raw = pd.read_csv(
        siata_csv or config.SIATA_RAW_CSV, usecols=["codigo_estacion", "fecha", "precipitacion_mm", "calidad"]
    )
    validos = (raw["calidad"] == 1) & (raw["precipitacion_mm"] >= 0)
    resumen = {"minutes_total": int(len(raw)), "minutes_discarded": int((~validos).sum())}
    df = raw.loc[validos].copy()
    local = timezone(timedelta(hours=utc_offset_hours))
    df["time_utc"] = pd.to_datetime(df["fecha"]).dt.tz_localize(local).dt.tz_convert("UTC").dt.floor("h")
    horas = (
        df.groupby(["codigo_estacion", "time_utc"])["precipitacion_mm"]
        .agg(precip_obs_mm="sum", valid_minutes="size")
        .reset_index()
        .rename(columns={"codigo_estacion": "station_id"})
    )
    horas["station_id"] = horas["station_id"].astype("int64")
    completas = horas["valid_minutes"] >= MIN_VALID_MINUTES
    resumen["hours_total"] = int(len(horas))
    resumen["hours_discarded_low_coverage"] = int((~completas).sum())
    horas = horas.loc[completas].copy()
    horas["rain_obs"] = horas["precip_obs_mm"] >= OBS_RAIN_MM
    return horas.reset_index(drop=True), resumen


def frequency_matched_threshold(values: pd.Series, target_rate: float) -> tuple[float, list[dict]]:
    tabla = [{"threshold_mm": t, "rate": round(float((values >= t).mean()), 4)} for t in THRESHOLD_GRID_MM]
    mejor = min(tabla, key=lambda r: (abs(r["rate"] - target_rate), r["threshold_mm"]))
    return mejor["threshold_mm"], tabla


def agreement(obs: pd.Series, pred: pd.Series) -> dict:
    obs, pred = pd.Series(obs, dtype=bool), pd.Series(pred, dtype=bool)
    p, r, f1, _ = precision_recall_fscore_support(obs, pred, average="binary", zero_division=0)
    kappa = cohen_kappa_score(obs, pred) if obs.nunique() > 1 or pred.nunique() > 1 else 0.0
    return {
        "n": int(len(obs)),
        "rate_obs": round(float(obs.mean()), 4),
        "rate_pred": round(float(pred.mean()), 4),
        "precision": round(float(p), 4),
        "recall": round(float(r), 4),
        "f1": round(float(f1), 4),
        "kappa": round(float(kappa), 4),
    }


def windowed(df: pd.DataFrame, hours: int, pred_col: str) -> pd.DataFrame:
    """Una ventana es lluviosa si alguna de sus horas lo es (mismo criterio para ambas fuentes)."""
    if hours == 1:
        return df[["rain_obs", pred_col]]
    w = df.assign(window=df["time_utc"].dt.floor(f"{hours}h"))
    return w.groupby(["station_id", "window"])[["rain_obs", pred_col]].any().reset_index(drop=True)


def _agreement_windowed(df: pd.DataFrame, hours: int, col: str) -> dict:
    w = windowed(df, hours, col)
    return agreement(w["rain_obs"], w[col])


def run(dataset: pd.DataFrame | None = None, siata_csv=None) -> dict:
    data = dataset if dataset is not None else pd.read_parquet(config.DATASET_PROCESSED)
    data = data[["station_id", "time_utc", "precipitation_ref", "precipitation", "era5_cell"]]
    horas, resumen_siata = siata_hourly(siata_csv)

    m = horas.merge(data, on=["station_id", "time_utc"], how="inner")
    inicio, fin = m["time_utc"].min(), m["time_utc"].max()
    corte = inicio + (fin - inicio) / 2
    calib, valid = m[m["time_utc"] < corte], m[m["time_utc"] >= corte]

    tasa_obs = float(calib["rain_obs"].mean())
    umbral_ref, tabla_ref = frequency_matched_threshold(calib["precipitation_ref"], tasa_obs)
    umbral_fc, tabla_fc = frequency_matched_threshold(calib["precipitation"], tasa_obs)

    valid = valid.assign(
        rain_label=valid["precipitation_ref"] >= umbral_ref,
        rain_forecast=valid["precipitation"] >= umbral_fc,
    )
    validacion = {}
    for col in ("rain_label", "rain_forecast"):
        validacion[col] = {
            "total": {f"{h}h": _agreement_windowed(valid, h, col) for h in WINDOWS_H},
            "by_station_1h": {
                str(sid): agreement(g["rain_obs"], g[col]) for sid, g in valid.groupby("station_id", sort=True)
            },
        }

    desfases = {}
    for off in OFFSETS_H:
        x = horas.assign(time_utc=horas["time_utc"] + pd.Timedelta(hours=off)).merge(
            data, on=["station_id", "time_utc"]
        )
        desfases[f"{off:+d}h"] = agreement(x["rain_obs"], x["precipitation_ref"] >= umbral_ref)["kappa"]

    hora_local = (m["time_utc"] + pd.Timedelta(hours=config.SIATA_UTC_OFFSET_HOURS)).dt.hour
    ciclo = (
        pd.DataFrame(
            {
                "siata": m["rain_obs"],
                "label": m["precipitation_ref"] >= umbral_ref,
                "forecast": m["precipitation"] >= umbral_fc,
            }
        )
        .groupby(hora_local.values)
        .mean()
        .round(4)
    )

    horas_validacion = valid.groupby("station_id").size()
    sin_datos = sorted(set(data["station_id"].unique()) - set(horas["station_id"].unique()))
    pocas_horas = sorted(int(s) for s, n in horas_validacion.items() if n < MIN_STATION_HOURS)

    return {
        "stations_without_valid_siata_data": [int(s) for s in sin_datos],
        "stations_below_min_validation_hours": {str(s): int(horas_validacion[s]) for s in pocas_horas},
        "min_validation_hours_per_station": MIN_STATION_HOURS,
        "siata_period_utc": [inicio.isoformat(), fin.isoformat()],
        "split_utc": corte.isoformat(),
        "siata_summary": resumen_siata,
        "obs_rain_threshold_mm": OBS_RAIN_MM,
        "calibration": {
            "rows": int(len(calib)),
            "rate_obs": round(tasa_obs, 4),
            "label_threshold_mm": umbral_ref,
            "label_grid": tabla_ref,
            "forecast_threshold_mm": umbral_fc,
            "forecast_grid": tabla_fc,
        },
        "config_label_threshold_mm": config.LABEL_THRESHOLD_MM,
        "config_matches_calibration": config.LABEL_THRESHOLD_MM == umbral_ref,
        "validation": {"rows": int(len(valid)), **validacion},
        "offset_kappa_label_1h": desfases,
        "diurnal_rain_rate_by_local_hour": ciclo.to_dict(orient="index"),
        "stations_by_era5_cell": {
            k: sorted(map(int, v)) for k, v in data.groupby("era5_cell")["station_id"].unique().items()
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    report = run()
    config.METRICS_DIR.mkdir(parents=True, exist_ok=True)
    openmeteo.write_atomic(
        config.LABEL_VALIDATION_REPORT,
        json.dumps(report, indent=2, ensure_ascii=False, default=_json_default).encode("utf-8") + b"\n",
    )
    cal, val = report["calibration"], report["validation"]
    log.info(
        "Umbral calibrado %.1f mm/h (config %.1f) · kappa 1h etiqueta=%.3f pronóstico=%.3f · kappa 6h etiqueta=%.3f",
        cal["label_threshold_mm"],
        report["config_label_threshold_mm"],
        val["rain_label"]["total"]["1h"]["kappa"],
        val["rain_forecast"]["total"]["1h"]["kappa"],
        val["rain_label"]["total"]["6h"]["kappa"],
    )
    if not report["config_matches_calibration"]:
        log.warning("LABEL_THRESHOLD_MM en mdva/config.py no coincide con la calibración: reconstruya el dataset")


def _json_default(o):
    if isinstance(o, np.generic):
        return o.item()
    raise TypeError(type(o))


if __name__ == "__main__":
    main()
