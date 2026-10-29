import abc
from typing import Any
from domain.entities import Location, Route

class MapRepository(abc.ABC):
    @abc.abstractmethod
    def load_graph(self) -> Any:
        """Carga o descarga el grafo de la ciudad."""
        pass

class RoutingService(abc.ABC):
    @abc.abstractmethod
    def find_shortest_path(self, origin: Location, destination: Location, graph: Any) -> Route:
        """Encuentra la ruta óptima en el grafo dado."""
        pass
