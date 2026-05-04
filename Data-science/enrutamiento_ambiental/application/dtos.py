from pydantic import BaseModel, ConfigDict
from typing import List, Optional

class Coordinate(BaseModel):
    latitude: float
    longitude: float

class RouteRequest(BaseModel):
    origin: Coordinate
    destination: Coordinate
    vehicle_type: str = "car" # car, motorcycle, bike

class MultiStopRouteRequest(BaseModel):
    """Solicitud de ruta con paradas intermedias."""
    waypoints: List[Coordinate]  # Mínimo 2 (origin + destination), las del medio son paradas
    vehicle_type: str = "car"

class RouteOption(BaseModel):
    distance_meters: float
    travel_time_seconds: float
    path: List[Coordinate]
    geometry_wkt: str
    rain_factor: float = 1.0
    rain_probability: float = 0.0
    rain_intensity_avg: float = 0.0
    elevation_avg: float = 1500.0
    route_type: str = "fastest"
    # ── Campos MDVA integrados ──
    mdva_llueve: bool = False
    mdva_probabilidad_rf: float = 0.0
    mdva_probabilidad_rl: float = 0.0
    mdva_temperatura_c: float = 0.0
    mdva_humedad_pct: float = 0.0
    mdva_cobertura_nubosa_pct: float = 0.0
    mdva_velocidad_viento_ms: float = 0.0
    # ── Alerta nivel MDVA ──
    alerta_nivel: str = "VERDE"  # VERDE, AMARILLO, ROJO
    alerta_mensaje: str = ""
    sugerir_ruta_alterna: bool = False

class RouteResponse(BaseModel):
    options: List[RouteOption]
    
    model_config = ConfigDict(from_attributes=True)

class MultiStopLeg(BaseModel):
    """Un tramo de la ruta multi-parada."""
    from_index: int
    to_index: int
    distance_meters: float
    travel_time_seconds: float
    path: List[Coordinate]
    rain_factor: float = 1.0
    rain_probability: float = 0.0
    rain_intensity_avg: float = 0.0
    elevation_avg: float = 1500.0
    # ── Campos MDVA integrados ──
    mdva_llueve: bool = False
    mdva_probabilidad_rf: float = 0.0
    mdva_probabilidad_rl: float = 0.0
    alerta_nivel: str = "VERDE"

class MultiStopRouteResponse(BaseModel):
    """Respuesta completa para ruta multi-parada."""
    legs: List[MultiStopLeg]
    total_distance_meters: float
    total_travel_time_seconds: float
    total_rain_factor: float
    total_rain_probability: float
    total_rain_intensity_avg: float
    waypoints: List[Coordinate]
    # ── Campos MDVA integrados ──
    mdva_llueve: bool = False
    mdva_probabilidad_rf: float = 0.0
    mdva_probabilidad_rl: float = 0.0
    alerta_nivel: str = "VERDE"
    alerta_mensaje: str = ""
    sugerir_ruta_alterna: bool = False

# ── DTOs para compatibilidad con Backend Spring Boot ──
class SpringRouteRequest(BaseModel):
    """Request que viene del Backend Spring Boot (mismo formato que TripRequestDTO)."""
    origen: Coordinate
    destino: Coordinate
    paradas: Optional[List[Coordinate]] = None
    vehicle_type: str = "car"

class SpringRouteStep(BaseModel):
    """Paso de navegación compatible con RouteStepDTO de Spring Boot."""
    instruccion: str
    distanciaMetros: int
    duracionSegundos: int
    startLat: float
    startLng: float
    endLat: float
    endLng: float

class SpringRouteResponse(BaseModel):
    """Respuesta compatible con lo que espera el Backend Spring Boot."""
    distanciaMetros: int
    duracionSegundos: int
    overviewPolyline: str  # encoded polyline compatible con Google Maps frontend
    pasos: List[SpringRouteStep]
    # ── Variables ambientales enriquecidas ──
    rain_factor: float = 1.0
    rain_probability: float = 0.0
    rain_intensity_avg: float = 0.0
    elevation_avg: float = 1500.0
    route_type: str = "fastest"
    mdva_llueve: bool = False
    mdva_probabilidad_rf: float = 0.0
    mdva_probabilidad_rl: float = 0.0
    mdva_temperatura_c: float = 0.0
    mdva_humedad_pct: float = 0.0
    mdva_cobertura_nubosa_pct: float = 0.0
    mdva_velocidad_viento_ms: float = 0.0
    alerta_nivel: str = "VERDE"
    alerta_mensaje: str = ""
    sugerir_ruta_alterna: bool = False
    # ── Rutas alternativas ──
    alternativas: Optional[List["SpringRouteResponse"]] = None

# Allow self-reference for alternativas
SpringRouteResponse.model_rebuild()
