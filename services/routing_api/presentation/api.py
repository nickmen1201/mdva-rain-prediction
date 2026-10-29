from application.dtos import (
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

router = APIRouter(prefix="/api/v1")


@router.post("/route", response_model=RouteResponse)
def calculate_route(request: RouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)):
    try:
        response = use_case.execute(request)
        return response
    except DomainException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/route/multi", response_model=MultiStopRouteResponse)
def calculate_multi_stop_route(
    request: MultiStopRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """Calcula una ruta que pasa por múltiples paradas intermedias."""
    try:
        response = use_case.execute_multi_stop(request)
        return response
    except DomainException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════════
# ENDPOINT PRINCIPAL PARA INTEGRACIÓN CON BACKEND SPRING BOOT
# ══════════════════════════════════════════════════════════════════════════════
# Este endpoint reemplaza la llamada a Google Directions API.
# El Backend Spring Boot llama a este en vez de Google, y recibe:
#   - Ruta calculada con OSMnx (grafo vial real del Valle de Aburrá)
#   - Variables ambientales integradas (MDVA ML + SIATA + Open-Meteo)
#   - Encoded polyline compatible con Google Maps frontend
#   - Pasos de navegación turn-by-turn
#   - Alerta de nivel climático (VERDE/AMARILLO/ROJO)


@router.post("/route/spring", response_model=SpringRouteResponse)
def calculate_spring_route(
    request: SpringRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """
    Endpoint compatible con el Backend Spring Boot (MDVA).
    Reemplaza Google Directions API con enrutamiento ambiental inteligente.

    Recibe el mismo formato que TripRequestDTO y retorna un formato
    compatible con GoogleMapsService.RouteResult enriquecido con
    variables ambientales.
    """
    try:
        response = use_case.execute_spring(request)
        return response
    except DomainException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


@router.post("/route/metrics")
def get_environmental_metrics(
    request: SpringRouteRequest, use_case: FindBestRouteUseCase = Depends(get_find_best_route_use_case)
):
    """
    Retorna ÚNICAMENTE las métricas ambientales (SIATA + Elevación + MDVA ML)
    sin calcular rutas en OSMnx.
    Ideal para enriquecer rutas provenientes de Google Maps en tiempo real.
    """
    try:
        # Usamos el weather_service inyectado
        ws = use_case.routing_svc.weather_service
        stats = ws.get_weather_stats(request.origen.latitude, request.origen.longitude)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
