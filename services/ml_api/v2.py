"""API v2: modelo rain_classifier (spec 005) con el contrato de features de mdva (spec 004).

Contrato: specs/006-ml-api-v2/contracts/openapi-v2.yaml. Errores en Problem Details (RFC 7807).
"""

from __future__ import annotations

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import AwareDatetime, BaseModel, Field, create_model

import monitoring
from mdva.features import RAW_INPUTS, FeatureInputError
from mdva.modeling.predict import RainModel, load_model

log = logging.getLogger(__name__)

MODEL_VERSION = os.environ.get("MDVA_MODEL_VERSION", "1.0.0")
_models_env = os.environ.get("MDVA_MODELS_DIR")
MODELS_DIR = Path(_models_env) if _models_env else Path(__file__).resolve().parents[2] / "models"
MAX_BATCH = 200

AlertLevel = Literal["VERDE", "AMARILLO", "ROJO"]
ChangeLevel = Literal["ESTABLE", "MODERADO", "SIGNIFICATIVO", "CRITICO"]

PredictionInput = create_model(
    "PredictionInput",
    time_utc=(AwareDatetime, Field(description="Instante objetivo con zona horaria (se normaliza a UTC)")),
    **{nombre: (float, Field(ge=col.min, le=col.max, description=col.unit)) for nombre, col in RAW_INPUTS.items()},
)


class Prediction(BaseModel):
    probability: float = Field(ge=0, le=1)
    alert_level: AlertLevel
    model_version: str


class BatchInput(BaseModel):
    records: list[PredictionInput] = Field(min_length=1, max_length=MAX_BATCH)


class BatchItem(BaseModel):
    probability: float = Field(ge=0, le=1)
    alert_level: AlertLevel


class BatchPrediction(BaseModel):
    model_version: str
    predictions: list[BatchItem]


class MonitorInput(BaseModel):
    probability_start: float = Field(ge=0, le=1)
    weather_timestamp_utc: AwareDatetime
    current: PredictionInput


class MonitorResult(BaseModel):
    probability_now: float = Field(ge=0, le=1)
    delta: float
    latency_minutes: int = Field(ge=0)
    stale_data: bool
    change_level: ChangeLevel
    model_version: str


class HealthModel(BaseModel):
    name: str
    version: str
    calibration: str


class HealthV2(BaseModel):
    status: Literal["ok"]
    ready: bool
    model: HealthModel


_state: dict[str, RainModel] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Falla el arranque si el modelo es incompatible con el entorno (FR-006)
    _state["model"] = load_model(MODEL_VERSION, models_dir=MODELS_DIR)
    log.info("Modelo %s cargado desde %s", MODEL_VERSION, MODELS_DIR)
    yield
    _state.clear()


def _model() -> RainModel:
    return _state["model"]


def _probabilities(records: list[BaseModel]) -> list[float]:
    filas = [r.model_dump() for r in records]
    return [float(p) for p in _model().predict_proba(filas)]


router = APIRouter(prefix="/v2", tags=["v2"])


@router.get("/health", response_model=HealthV2)
def health_v2():
    m = _model().metadata
    return HealthV2(
        status="ok",
        ready=True,
        model=HealthModel(name=m["model_name"], version=m["model_version"], calibration=m["calibration"]["method"]),
    )


@router.post("/predict", response_model=Prediction)
def predict_v2(entrada: PredictionInput):
    p = _probabilities([entrada])[0]
    return Prediction(probability=p, alert_level=_model().alert_level(p), model_version=MODEL_VERSION)


@router.post("/predict/batch", response_model=BatchPrediction)
def predict_batch_v2(lote: BatchInput):
    m = _model()
    items = [BatchItem(probability=p, alert_level=m.alert_level(p)) for p in _probabilities(lote.records)]
    return BatchPrediction(model_version=MODEL_VERSION, predictions=items)


@router.post("/monitor/trip", response_model=MonitorResult)
def monitor_trip_v2(req: MonitorInput):
    p_now = _probabilities([req.current])[0]
    latencia = monitoring.latency_minutes(req.weather_timestamp_utc, datetime.now(timezone.utc))
    return MonitorResult(
        probability_now=p_now,
        delta=p_now - req.probability_start,
        latency_minutes=latencia,
        stale_data=latencia > monitoring.LATENCIA_MAX_MIN,
        change_level=monitoring.change_level(req.probability_start, p_now, latencia),
        model_version=MODEL_VERSION,
    )


# ── Problem Details (RFC 7807), solo para /v2 ────────────────────────────────


def _problem(status: int, title: str, request: Request, detail: str, errors: list[dict] | None = None):
    body = {"type": "about:blank", "title": title, "status": status, "detail": detail, "instance": request.url.path}
    if errors is not None:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    default_validation = app.exception_handlers.get(RequestValidationError)

    @app.exception_handler(RequestValidationError)
    async def validation(request: Request, exc: RequestValidationError):
        if not request.url.path.startswith("/v2"):
            from fastapi.exception_handlers import request_validation_exception_handler

            return await (default_validation or request_validation_exception_handler)(request, exc)
        errores = [{"field": ".".join(str(p) for p in e["loc"] if p != "body"), "rule": e["msg"]} for e in exc.errors()]
        return _problem(422, "Entrada inválida", request, "La petición no cumple el contrato de entradas.", errores)

    @app.exception_handler(FeatureInputError)
    async def feature_input(request: Request, exc: FeatureInputError):
        errores = [{"field": campo, "rule": regla} for campo, regla in exc.problems]
        return _problem(422, "Entrada inválida", request, "La petición no cumple el contrato de features.", errores)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        if not request.url.path.startswith("/v2"):
            return PlainTextResponse("Internal Server Error", status_code=500)  # respuesta por defecto de v1
        error_id = uuid.uuid4().hex
        log.exception("Error interno %s en %s", error_id, request.url.path)
        return _problem(500, "Error interno", request, f"Error interno; referencia {error_id}.")
