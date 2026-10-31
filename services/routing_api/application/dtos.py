"""DTOs del routing service (contrato: specs/009-routing-cleanup/contracts/routing-api.md y spec 010).

Los campos de lluvia salen de una sola señal (modelo v2 vía ML API); si no hay clima,
`clima_disponible=false` y los campos de probabilidad/alerta son nulos (nunca valores por defecto).
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class RainInfo(BaseModel):
    """Señal de lluvia usada para la ruta (aplanada en cada respuesta)."""

    clima_disponible: bool = False
    rain_probability: Optional[float] = None  # [0, 1], modelo v2 en el origen
    alerta_nivel: Optional[str] = None  # VERDE | AMARILLO | ROJO (RF-10)
    model_version: Optional[str] = None
    rain_factor: float = 1.0  # factor RF-10 aplicado al tiempo


class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    vehicle_type: str = "car"  # car | motorcycle | bike


class MultiStopRouteRequest(BaseModel):
    """Solicitud de ruta con paradas intermedias."""

    waypoints: List[Coordinate]  # mínimo 2 (origen + destino); las del medio son paradas
    vehicle_type: str = "car"


class RouteOption(RainInfo):
    distance_meters: float
    travel_time_seconds: float
    path: List[Coordinate]
    geometry_wkt: str
    route_type: str = "fastest"
    rain_exposure: Optional[float] = None  # P(lluvia) media ponderada por tiempo (spec 010)


class RouteResponse(BaseModel):
    options: List[RouteOption]
    dryest_available: bool = False

    model_config = ConfigDict(from_attributes=True)


class MultiStopLeg(BaseModel):
    """Un tramo de la ruta multi-parada."""

    from_index: int
    to_index: int
    distance_meters: float
    travel_time_seconds: float
    path: List[Coordinate]


class MultiStopRouteResponse(RainInfo):
    """Respuesta completa para ruta multi-parada (la señal de lluvia es la del origen del viaje)."""

    legs: List[MultiStopLeg]
    total_distance_meters: float
    total_travel_time_seconds: float
    waypoints: List[Coordinate]


# ── DTOs para compatibilidad con el Backend Spring Boot ──
class SpringRouteRequest(BaseModel):
    """Request que viene del Backend Spring Boot."""

    origen: Coordinate
    destino: Coordinate
    paradas: Optional[List[Coordinate]] = None
    vehicle_type: str = "car"
    route_type: str = "fastest"  # fastest | dryest | shortest


class SpringRouteStep(BaseModel):
    """Paso de navegación compatible con RouteStepDTO de Spring Boot."""

    instruccion: str
    distanciaMetros: int
    duracionSegundos: int
    startLat: float
    startLng: float
    endLat: float
    endLng: float


class SpringRouteResponse(RainInfo):
    """Respuesta que consume el Backend: geometría, duración base y pasos (spec 008)."""

    distanciaMetros: int
    duracionSegundos: int  # base: el ajuste RF-10 lo aplica el Backend
    overviewPolyline: str  # encoded polyline (precisión 5)
    pasos: List[SpringRouteStep]
    route_type: str = "fastest"
    rain_exposure: Optional[float] = None
    dryest_available: bool = False
    alternativas: Optional[List["SpringRouteResponse"]] = None


SpringRouteResponse.model_rebuild()


class MetricsResponse(RainInfo):
    """Solo la señal de lluvia para un punto (RF-15 `/route/metrics`)."""

    time_utc: Optional[str] = None
