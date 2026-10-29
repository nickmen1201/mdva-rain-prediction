"""Construye el dataset de modelado de lluvia (spec 003).

raw      data/raw/openmeteo/{forecast,era5}/{año}.json  (+ CSV crudo de SIATA, solo catálogo)
interim  data/interim/openmeteo_{forecast,era5}.parquet
processed data/processed/rain_hourly.parquet  (contrato rain_hourly)

Cada etapa se valida contra su contrato antes de escribirse; si falla, no se promueve
y el motivo queda en reports/data_quality.json.

Uso (desde la raíz del repo):
    python -m mdva.dataset
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
from pathlib import Path

import pandas as pd

from mdva import config, openmeteo
from mdva.data_contract import (
    DATASET_CONTRACT,
    FORECAST_INTERIM_CONTRACT,
    REFERENCE_INTERIM_CONTRACT,
    Contract,
    DataContractError,
    validate,
)

log = logging.getLogger(__name__)

KEY = ["station_id", "time_utc"]


# ── Catálogo de estaciones ───────────────────────────────────────────────────


def build_stations(siata_csv: Path) -> pd.DataFrame:
    cols = {
        "codigo_estacion": "station_id",
        "estacion": "name",
        "ciudad": "municipality",
        "latitud": "latitude",
        "longitud": "longitude",
    }
    df = pd.read_csv(siata_csv, usecols=list(cols)).rename(columns=cols)
    df = df.drop_duplicates("station_id").sort_values("station_id").reset_index(drop=True)
    df["station_id"] = df["station_id"].astype("int64")
    return df[list(cols.values())]


# ── raw → interim ────────────────────────────────────────────────────────────


def parse_raw(paths: list[Path], station_ids: list[int], source: str) -> pd.DataFrame:
    """Convierte las respuestas crudas (una lista de ubicaciones por archivo) a formato largo."""
    partes = []
    for path in paths:
        respuestas = json.loads(path.read_text(encoding="utf-8"))
        respuestas = respuestas if isinstance(respuestas, list) else [respuestas]
        for sid, r in zip(station_ids, respuestas, strict=True):
            h = pd.DataFrame(r["hourly"])
            h.insert(0, "station_id", sid)
            h["time_utc"] = pd.to_datetime(h.pop("time"), utc=True)
            if source == "era5":
                h = h.rename(columns={"precipitation": "precipitation_ref"})
                h["era5_cell"] = f"{r['latitude']},{r['longitude']}"
            partes.append(h)
    df = pd.concat(partes, ignore_index=True)
    df["station_id"] = df["station_id"].astype("int64")
    contract = FORECAST_INTERIM_CONTRACT if source == "forecast" else REFERENCE_INTERIM_CONTRACT
    cols = [c.name for c in contract.columns if c.name in df.columns]  # las faltantes las reporta el contrato
    for col in contract.columns[2:]:
        if col.dtype == "float64" and col.name in df.columns:
            df[col.name] = df[col.name].astype("float64")
    return df[cols].sort_values(KEY).reset_index(drop=True)


# ── interim → processed ──────────────────────────────────────────────────────


def build_processed(
    forecast: pd.DataFrame, reference: pd.DataFrame, stations: pd.DataFrame, threshold_mm: float
) -> tuple[pd.DataFrame, dict]:
    """Une pronóstico y referencia, descarta filas incompletas (sin imputar) y etiqueta."""
    df = forecast.merge(reference, on=KEY, how="inner", validate="one_to_one")
    df = df.merge(
        stations[["station_id", "latitude", "longitude"]], on="station_id", how="left", validate="many_to_one"
    )
    features = [c.name for c in FORECAST_INTERIM_CONTRACT.columns][2:]
    incompletas = df[features + ["precipitation_ref"]].isna().any(axis=1)
    descartes = df.loc[incompletas].groupby("station_id").size().astype(int).to_dict()
    df = df.loc[~incompletas].copy()
    df["rain"] = df["precipitation_ref"] >= threshold_mm
    df = df[[c.name for c in DATASET_CONTRACT.columns]].sort_values(KEY).reset_index(drop=True)
    resumen = {
        "joined_rows": int(len(df) + incompletas.sum()),
        "dropped_incomplete_rows": int(incompletas.sum()),
        "dropped_by_station": {str(k): v for k, v in descartes.items()},
        "label_threshold_mm": threshold_mm,
        "rain_rate": round(float(df["rain"].mean()), 4) if len(df) else None,
        "rows_by_station": {str(k): int(v) for k, v in df.groupby("station_id").size().items()},
        "stations_by_era5_cell": {
            k: sorted(map(int, v)) for k, v in df.groupby("era5_cell")["station_id"].unique().items()
        },
    }
    return df, resumen


# ── Utilidades ───────────────────────────────────────────────────────────────


def content_fingerprint(df: pd.DataFrame) -> str:
    """Huella del contenido, independiente del formato del archivo (research R3)."""
    hashes = pd.util.hash_pandas_object(df.sort_values(KEY).reset_index(drop=True), index=False)
    return hashlib.sha256(hashes.to_numpy().tobytes()).hexdigest()


def write_stage(df: pd.DataFrame, contract: Contract, path: Path, report: dict) -> None:
    """Valida contra el contrato y solo entonces escribe (de forma atómica)."""
    try:
        resultado = validate(df, contract)
    except DataContractError as e:
        report["stages"][contract.name] = e.report.to_dict()
        raise
    report["stages"][contract.name] = resultado.to_dict() | {"content_fingerprint": content_fingerprint(df)}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def write_report(report: dict, path: Path) -> None:
    openmeteo.write_atomic(path, json.dumps(report, indent=2, ensure_ascii=False).encode("utf-8") + b"\n")


# ── Pipeline ─────────────────────────────────────────────────────────────────


def run(fetcher=openmeteo.fetch) -> dict:
    report: dict = {"dataset_contract_version": DATASET_CONTRACT.version, "downloads": {}, "stages": {}}
    try:
        stations = build_stations(config.SIATA_RAW_CSV)
        config.EXTERNAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        stations.to_csv(config.STATIONS_CSV, index=False, lineterminator="\n")
        report["stations"] = int(len(stations))

        manifest = openmeteo.Manifest(config.RAW_MANIFEST, config.RAW_DATA_DIR)
        siata = config.SIATA_RAW_CSV
        if not manifest.is_intact(siata):
            manifest.record(siata, "siata", None)

        ids = stations["station_id"].tolist()
        lats, lons = stations["latitude"].tolist(), stations["longitude"].tolist()
        crudos: dict[str, list[Path]] = {"forecast": [], "era5": []}
        for source in crudos:
            nuevos = 0
            for year in config.YEARS:
                ruta, descargado = openmeteo.download_year(
                    source, year, lats, lons, manifest, config.OPENMETEO_RAW_DIR, fetcher=fetcher
                )
                crudos[source].append(ruta)
                nuevos += descargado
            report["downloads"][source] = {"new": nuevos, "cached": len(config.YEARS) - nuevos}

        forecast = parse_raw(crudos["forecast"], ids, "forecast")
        write_stage(forecast, FORECAST_INTERIM_CONTRACT, config.FORECAST_INTERIM, report)
        reference = parse_raw(crudos["era5"], ids, "era5")
        write_stage(reference, REFERENCE_INTERIM_CONTRACT, config.REFERENCE_INTERIM, report)

        dataset, resumen = build_processed(forecast, reference, stations, config.LABEL_THRESHOLD_MM)
        report["processed_summary"] = resumen
        write_stage(dataset, DATASET_CONTRACT, config.DATASET_PROCESSED, report)
        report["ok"] = True
        return report
    except DataContractError:
        report["ok"] = False
        raise
    finally:
        write_report(report, config.DATA_QUALITY_REPORT)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    report = run()
    log.info(
        "Dataset listo: %s filas, tasa de lluvia %s, descargas nuevas %s",
        report["stages"][DATASET_CONTRACT.name]["rows"],
        report["processed_summary"]["rain_rate"],
        {k: v["new"] for k, v in report["downloads"].items()},
    )


if __name__ == "__main__":
    main()
