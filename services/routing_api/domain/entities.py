from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class Location:
    latitude: float
    longitude: float


@dataclass
class Route:
    """Ruta sobre el grafo. Sin campos del regresor de intensidad retirado (spec 009)."""

    distance_meters: float
    travel_time_seconds: float  # Σ tiempo de arista × factor RF-10
    path: List[Location]
    segments: List[Any] = field(default_factory=list)  # application.navigation.Segment
    route_type: str = "fastest"  # fastest | shortest | dryest
    rain_factor: float = 1.0  # factor RF-10 aplicado al tiempo (1.0 sin señal de lluvia)
    rain_exposure: float | None = None  # P(lluvia) media ponderada por tiempo (spec 010)
