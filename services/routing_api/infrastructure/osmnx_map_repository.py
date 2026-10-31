import logging
import os

import osmnx as ox
from domain.ports import MapRepository

log = logging.getLogger(__name__)

# Los 10 municipios del Valle de Aburrá (charter RF-04)
MUNICIPIOS = [
    "Medellín, Antioquia, Colombia",
    "Bello, Antioquia, Colombia",
    "Itagüí, Antioquia, Colombia",
    "Envigado, Antioquia, Colombia",
    "Sabaneta, Antioquia, Colombia",
    "La Estrella, Antioquia, Colombia",
    "Caldas, Antioquia, Colombia",
    "Copacabana, Antioquia, Colombia",
    "Girardota, Antioquia, Colombia",
    "Barbosa, Antioquia, Colombia",
]


def ensure_travel_times(graph) -> bool:
    """Agrega `speed_kph` y `travel_time` (s) por arista si faltan (spec 009, R-30).

    Velocidad desde `maxspeed` de OSM o, si falta, la media de su tipo de vía en el grafo
    (`ox.add_edge_speeds`). Devuelve True si modificó el grafo.
    """
    if all("travel_time" in d for _, _, d in graph.edges(data=True)):
        return False
    ox.add_edge_speeds(graph)
    ox.add_edge_travel_times(graph)
    return True


class OSMnxMapRepository(MapRepository):
    def __init__(self, place_name=None, cache_file="valle_aburra.graphml"):
        self.place_name = place_name or MUNICIPIOS
        self.cache_file = cache_file
        self._cached_graph = None

    def load_graph(self):
        if self._cached_graph is not None:
            return self._cached_graph

        if os.path.exists(self.cache_file):
            log.info("Cargando grafo desde caché local: %s", self.cache_file)
            graph = ox.load_graphml(self.cache_file)
        else:
            log.info("Descargando grafo del Valle de Aburrá (puede tardar varios minutos)...")
            graph = ox.graph_from_place(self.place_name, network_type="drive")

        if ensure_travel_times(graph) or not os.path.exists(self.cache_file):
            # Un grafo cacheado antes de la spec 009 no tiene tiempos: se calculan una vez y se guardan
            log.info("Guardando grafo con velocidades y tiempos en caché: %s", self.cache_file)
            ox.save_graphml(graph, self.cache_file)

        self._cached_graph = graph
        return graph
