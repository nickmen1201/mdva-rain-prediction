from dataclasses import dataclass
from typing import List

@dataclass
class Location:
    latitude: float
    longitude: float

@dataclass
class Route:
    distance_meters: float
    travel_time_seconds: float
    path: List[Location]
    geometry_wkt: str = ""
    rain_factor: float = 1.0
    rain_probability: float = 0.0 # Porcentaje 0-100
    rain_intensity_avg: float = 0.0 # mm/h promedio
    elevation_avg: float = 1500.0 # Metros sobre el nivel del mar
    route_type: str = "fastest" # fastest, dryest, balanced
    # ── Campos MDVA integrados ──
    mdva_llueve: bool = False
    mdva_probabilidad_rf: float = 0.0  # Probabilidad Random Forest (0-1)
    mdva_probabilidad_rl: float = 0.0  # Probabilidad Regresión Logística (0-1)
    mdva_temperatura_c: float = 0.0
    mdva_humedad_pct: float = 0.0
    mdva_cobertura_nubosa_pct: float = 0.0
    mdva_velocidad_viento_ms: float = 0.0
