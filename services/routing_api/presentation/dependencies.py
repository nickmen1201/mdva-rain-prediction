import os

from application.use_cases import FindBestRouteUseCase
from infrastructure.networkx_routing_service import NetworkXRoutingService
from infrastructure.osmnx_map_repository import OSMnxMapRepository
from infrastructure.rain_signal import RainSignalClient

# Configuración desde variables de entorno
MDVA_ML_URL = os.environ.get("MDVA_ML_URL", "http://ml-service:8081")
GRAPH_CACHE_FILE = os.environ.get("GRAPH_CACHE_FILE", "valle_aburra.graphml")

# Instancias únicas: el grafo queda en memoria entre peticiones
_map_repository = OSMnxMapRepository(cache_file=GRAPH_CACHE_FILE)
_routing_service = NetworkXRoutingService(RainSignalClient(MDVA_ML_URL))
_find_route_use_case = FindBestRouteUseCase(_map_repository, _routing_service)


def get_find_best_route_use_case() -> FindBestRouteUseCase:
    return _find_route_use_case
