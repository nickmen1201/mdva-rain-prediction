import abc
from typing import Any


class MapRepository(abc.ABC):
    @abc.abstractmethod
    def load_graph(self) -> Any:
        """Carga o descarga el grafo de la ciudad."""
