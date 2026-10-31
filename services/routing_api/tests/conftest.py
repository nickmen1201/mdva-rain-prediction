import math
import sys
from pathlib import Path

import networkx as nx
import pytest

# Los módulos del servicio (domain, application, ...) se importan desde services/routing_api/
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Nodos (lat, lon) del grafo sintético: dos caminos entre A (oeste) y B (este)
#   corto y lento:  A → C → B por "Calle 10" (residencial, 30 km/h)
#   largo y rápido: A → D → E → B por "Avenida Oriental" (primaria, 80 km/h)
NODOS = {
    "A": (6.2000, -75.5800),
    "C": (6.2000, -75.5700),
    "B": (6.2000, -75.5600),
    "D": (6.2050, -75.5800),
    "E": (6.2050, -75.5600),
}
IDS = {nombre: i for i, nombre in enumerate(NODOS)}


def _metros(a, b):
    (lat1, lon1), (lat2, lon2) = NODOS[a], NODOS[b]
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    h = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def build_graph():
    """Grafo OSMnx mínimo (sin velocidades: las agrega el repositorio)."""
    g = nx.MultiDiGraph(crs="epsg:4326")
    for nombre, (lat, lon) in NODOS.items():
        g.add_node(IDS[nombre], y=lat, x=lon)
    tramos = [
        ("A", "C", "residential", "Calle 10", "30"),
        ("C", "B", "residential", "Calle 10", "30"),
        ("A", "D", "primary", "Avenida Oriental", "80"),
        ("D", "E", "primary", "Avenida Oriental", "80"),
        ("E", "B", "primary", "Avenida Oriental", "80"),
    ]
    for u, v, highway, name, maxspeed in tramos:
        for a, b in ((u, v), (v, u)):
            g.add_edge(IDS[a], IDS[b], length=_metros(a, b), highway=highway, name=name, maxspeed=maxspeed)
    return g


@pytest.fixture
def graph():
    return build_graph()
