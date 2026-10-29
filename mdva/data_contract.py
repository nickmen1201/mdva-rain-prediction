"""Contratos de datos y validación por etapa (constitución V, spec 003).

Cada contrato declara columnas (tipo, unidad, rango, nulabilidad), clave única y
cobertura temporal esperada. `validate` evalúa todas las reglas, deja el resultado de
cada una en un `QualityReport` y lanza `DataContractError` si alguna falla, para que
el pipeline no promueva datos inválidos a la etapa siguiente.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

import pandas as pd

from mdva import config

DATASET_CONTRACT_VERSION = "1.0.0"

PERIOD_START = pd.Timestamp(f"{config.YEARS[0]}-01-01T00:00", tz="UTC")
PERIOD_END = pd.Timestamp(f"{config.YEARS[-1]}-12-31T23:00", tz="UTC")


@dataclass(frozen=True)
class Column:
    name: str
    dtype: str
    unit: str | None = None
    min: float | None = None
    max: float | None = None
    nullable: bool = False


@dataclass(frozen=True)
class Contract:
    name: str
    version: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    group_column: str = "station_id"
    time_column: str = "time_utc"
    period_start: pd.Timestamp = PERIOD_START
    period_end: pd.Timestamp = PERIOD_END
    min_coverage: float = 0.99
    max_null_fraction: float = 0.01

    @property
    def expected_hours(self) -> int:
        return int((self.period_end - self.period_start) / pd.Timedelta(hours=1)) + 1


@dataclass
class RuleResult:
    rule: str
    ok: bool
    detail: str = ""

    def __post_init__(self):
        self.ok = bool(self.ok)  # las comparaciones de pandas devuelven numpy.bool_


@dataclass
class QualityReport:
    contract: str
    version: str
    rows: int
    results: list[RuleResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def failures(self) -> list[RuleResult]:
        return [r for r in self.results if not r.ok]

    def to_dict(self) -> dict:
        return {
            "contract": self.contract,
            "version": self.version,
            "rows": self.rows,
            "ok": self.ok,
            "rules": [asdict(r) for r in self.results],
        }


class DataContractError(Exception):
    def __init__(self, report: QualityReport):
        self.report = report
        fallas = "; ".join(f"{r.rule}: {r.detail}" for r in report.failures())
        super().__init__(f"Contrato '{report.contract}' v{report.version} violado → {fallas}")


# ── Contratos ────────────────────────────────────────────────────────────────

_FORECAST_COLUMNS = (
    Column("temperature_2m", "float64", "degC", -5, 45),
    Column("relative_humidity_2m", "float64", "%", 0, 100),
    Column("dew_point_2m", "float64", "degC", -20, 35),
    Column("cloud_cover", "float64", "%", 0, 100),
    Column("wind_speed_10m", "float64", "m/s", 0, 60),
    Column("wind_direction_10m", "float64", "deg", 0, 360),
    Column("pressure_msl", "float64", "hPa", 950, 1050),
    Column("precipitation", "float64", "mm/h", 0, 200),
    Column("cape", "float64", "J/kg", 0, 10000),
)

_KEY = (Column("station_id", "int64"), Column("time_utc", "datetime64[us, UTC]"))

FORECAST_INTERIM_CONTRACT = Contract(
    name="openmeteo_forecast",
    version="1.0.0",
    columns=_KEY + tuple(Column(c.name, c.dtype, c.unit, c.min, c.max, nullable=True) for c in _FORECAST_COLUMNS),
    primary_key=("station_id", "time_utc"),
)

REFERENCE_INTERIM_CONTRACT = Contract(
    name="openmeteo_era5",
    version="1.0.0",
    columns=_KEY
    + (
        Column("precipitation_ref", "float64", "mm/h", 0, 200, nullable=True),
        Column("era5_cell", "str"),
    ),
    primary_key=("station_id", "time_utc"),
)

DATASET_CONTRACT = Contract(
    name="rain_hourly",
    version=DATASET_CONTRACT_VERSION,
    columns=_KEY
    + (
        Column("latitude", "float64", "deg", 6.0, 6.6),
        Column("longitude", "float64", "deg", -75.8, -75.2),
    )
    + _FORECAST_COLUMNS
    + (
        Column("precipitation_ref", "float64", "mm/h", 0, 200),
        Column("era5_cell", "str"),
        Column("rain", "bool"),
    ),
    primary_key=("station_id", "time_utc"),
)

# Unidades que la fuente debe declarar en `hourly_units` (research R7)
EXPECTED_FORECAST_UNITS = {
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
EXPECTED_REFERENCE_UNITS = {"precipitation": "mm"}


# ── Validación ───────────────────────────────────────────────────────────────


def validate_units(units: dict, expected: dict, source: str) -> None:
    """Verifica las unidades declaradas por la fuente (detecta, p. ej., viento en km/h)."""
    distintas = {k: (units.get(k), v) for k, v in expected.items() if units.get(k) != v}
    report = QualityReport(contract=f"units:{source}", version="-", rows=0)
    detalle = ", ".join(f"{k}: recibido {got!r}, esperado {exp!r}" for k, (got, exp) in distintas.items())
    report.results.append(RuleResult("units", not distintas, detalle))
    if not report.ok:
        raise DataContractError(report)


def validate(df: pd.DataFrame, contract: Contract, *, raise_on_error: bool = True) -> QualityReport:
    report = QualityReport(contract=contract.name, version=contract.version, rows=len(df))
    add = report.results.append
    expected = [c.name for c in contract.columns]

    faltantes = [c for c in expected if c not in df.columns]
    sobrantes = [c for c in df.columns if c not in expected]
    add(RuleResult("columns", not faltantes and not sobrantes, f"faltan={faltantes} sobran={sobrantes}"))
    if faltantes:
        return _finish(report, raise_on_error)

    for col in contract.columns:
        s = df[col.name]
        add(RuleResult(f"dtype:{col.name}", str(s.dtype) == col.dtype, f"{s.dtype} (esperado {col.dtype})"))

        nulos = int(s.isna().sum())
        if col.nullable:
            peor = s.isna().groupby(df[contract.group_column]).mean().max() if len(df) else 0.0
            add(
                RuleResult(
                    f"nulls:{col.name}",
                    peor <= contract.max_null_fraction,
                    f"peor fracción por {contract.group_column}={peor:.4f} (máx {contract.max_null_fraction})",
                )
            )
        else:
            add(RuleResult(f"nulls:{col.name}", nulos == 0, f"{nulos} nulos"))

        if col.min is not None or col.max is not None:
            fuera = s.dropna()
            fuera = fuera[(fuera < col.min) | (fuera > col.max)]
            add(
                RuleResult(
                    f"range:{col.name}",
                    fuera.empty,
                    f"{len(fuera)} fuera de [{col.min}, {col.max}] {col.unit or ''}".strip(),
                )
            )

    duplicados = int(df.duplicated(list(contract.primary_key)).sum())
    add(RuleResult("unique_key", duplicados == 0, f"{duplicados} duplicados de {list(contract.primary_key)}"))

    t = df[contract.time_column]
    en_periodo = (t >= contract.period_start) & (t <= contract.period_end)
    add(RuleResult("period", bool(en_periodo.all()), f"{int((~en_periodo).sum())} filas fuera del periodo"))

    cobertura = (
        df[en_periodo].groupby(contract.group_column)[contract.time_column].nunique().div(contract.expected_hours)
    )
    peor = float(cobertura.min()) if len(cobertura) else 0.0
    add(
        RuleResult(
            "coverage",
            peor >= contract.min_coverage,
            f"peor cobertura por {contract.group_column}={peor:.4f} (mín {contract.min_coverage})",
        )
    )
    return _finish(report, raise_on_error)


def _finish(report: QualityReport, raise_on_error: bool) -> QualityReport:
    if raise_on_error and not report.ok:
        raise DataContractError(report)
    return report
