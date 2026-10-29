import os
from infrastructure.osmnx_map_repository import OSMnxMapRepository
from infrastructure.networkx_routing_service import NetworkXRoutingService
from infrastructure.weather_service import WeatherService
from domain.rain_model import RainModel
from application.use_cases import FindBestRouteUseCase

# Configuración desde variables de entorno
MDVA_ML_URL = os.environ.get("MDVA_ML_URL", "http://ml-service:8081")
GRAPH_CACHE_FILE = os.environ.get("GRAPH_CACHE_FILE", "valle_aburra.graphml")
RAIN_MODEL_PATH = os.environ.get("RAIN_MODEL_PATH", "./cache/rain_model.joblib")

# Instancias Singleton para mantener el grafo en memoria y evitar pasajes innecesarios
_map_repository = OSMnxMapRepository(cache_file=GRAPH_CACHE_FILE)
_rain_model = RainModel(model_path=RAIN_MODEL_PATH)
_weather_service = WeatherService(_rain_model, mdva_ml_url=MDVA_ML_URL)
_routing_service = NetworkXRoutingService(_weather_service)
_find_route_use_case = FindBestRouteUseCase(_map_repository, _routing_service)

def get_find_best_route_use_case() -> FindBestRouteUseCase:
    return _find_route_use_case
