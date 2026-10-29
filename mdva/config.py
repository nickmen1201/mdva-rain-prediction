"""Rutas y constantes del proyecto.

Único lugar donde se definen rutas (charter E-04) y parámetros del dataset; el resto
del código los importa de aquí.
"""

from pathlib import Path

PROJ_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
EXTERNAL_DATA_DIR = DATA_DIR / "external"

MODELS_DIR = PROJ_ROOT / "models"

REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
METRICS_DIR = REPORTS_DIR / "metrics"

# ── Dataset de lluvia (spec 003) ──────────────────────────────────────────────

SIATA_RAW_CSV = RAW_DATA_DIR / "siata" / "precipitacion_siata_plano.csv"
STATIONS_CSV = EXTERNAL_DATA_DIR / "siata_stations.csv"
OPENMETEO_RAW_DIR = RAW_DATA_DIR / "openmeteo"
RAW_MANIFEST = RAW_DATA_DIR / "MANIFEST.json"

FORECAST_INTERIM = INTERIM_DATA_DIR / "openmeteo_forecast.parquet"
REFERENCE_INTERIM = INTERIM_DATA_DIR / "openmeteo_era5.parquet"
DATASET_PROCESSED = PROCESSED_DATA_DIR / "rain_hourly.parquet"

DATA_QUALITY_REPORT = REPORTS_DIR / "data_quality.json"
LABEL_VALIDATION_REPORT = METRICS_DIR / "label_validation.json"

YEARS = (2022, 2023, 2024, 2025)

# Variables de pronóstico disponibles en el histórico y en vivo (research R1)
FORECAST_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "cloud_cover",
    "wind_speed_10m",
    "wind_direction_10m",
    "pressure_msl",
    "precipitation",
    "cape",
)

# Precipitación horaria de referencia (ERA5) a partir de la cual una hora cuenta como
# "llueve". Calibrado por igualación de frecuencias con la primera mitad del mes de
# pluviómetros SIATA (spec 003, research R4; ver reports/metrics/label_validation.json).
LABEL_THRESHOLD_MM = 0.5

# Zona horaria de los timestamps de SIATA (research R5)
SIATA_UTC_OFFSET_HOURS = -5
