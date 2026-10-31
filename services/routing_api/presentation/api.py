import logging

from application.dtos import (
    MetricsResponse,
    MultiStopRouteRequest,
    MultiStopRouteResponse,
    RouteRequest,
    RouteResponse,
    SpringRouteRequest,
    SpringRouteResponse,
)
from application.use_cases import FindBestRouteUseCase
from domain.exceptions import DomainException
from fastapi import APIRouter, Depends, HTTPException
from presentation.dependencies import get_find_best_route_use_case

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")


def _run(fn, request):
    try:
        return fn(request)
    except (DomainException, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        # El detalle interno se loguea; al cliente, un mensaje genérico (constitución IV)
        log.exception("Error calculando la ruta")
        raise HTTPException(status_code=500, detail="Error interno calculando la ruta") from e


@router.post("/route", response_model=RouteResponse)
def calculate_route(request: RouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)):
    """Opciones `fastest`, `shortest` y, si hay grilla de lluvia, `dryest`."""
    return _run(use_case.execute, request)


@router.post("/route/multi", response_model=MultiStopRouteResponse)
def calculate_multi_stop_route(
    request: MultiStopRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """Ruta que pasa por múltiples paradas en el orden recibido."""
    return _run(use_case.execute_multi_stop, request)


@router.post("/route/spring", response_model=SpringRouteResponse)
def calculate_spring_route(
    request: SpringRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """Endpoint que consume el Backend (spec 008): geometría, duración base, pasos y alternativas."""
    return _run(use_case.execute_spring, request)


@router.post("/route/metrics", response_model=MetricsResponse)
def get_environmental_metrics(
    request: SpringRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """Solo la señal de lluvia del origen (modelo v2), sin calcular rutas."""
    return _run(use_case.metrics, request)
