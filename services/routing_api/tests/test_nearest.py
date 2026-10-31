"""NearestNodeIndex: mismo resultado que la búsqueda por haversine (spec 009)."""

import math

from conftest import IDS, NODOS
from infrastructure.nearest import NearestNodeIndex


def _haversine(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6_371_000 * math.asin(math.sqrt(h))


def test_nodo_exacto(graph):
    index = NearestNodeIndex(graph)
    for nombre, (lat, lon) in NODOS.items():
        assert index.nearest(lat, lon) == IDS[nombre]


def test_coincide_con_haversine_en_una_malla(graph):
    index = NearestNodeIndex(graph)
    for i in range(15):
        for j in range(15):
            lat, lon = 6.195 + i * 0.001, -75.585 + j * 0.0018
            esperado = min(NODOS, key=lambda n: _haversine(lat, lon, *NODOS[n]))
            assert index.nearest(lat, lon) == IDS[esperado]


def test_devuelve_tipo_python(graph):
    assert isinstance(NearestNodeIndex(graph).nearest(6.2, -75.58), int)
