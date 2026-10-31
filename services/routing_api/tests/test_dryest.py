"""`dryest` real: la penalización varía por arista según una grilla espacial (spec 010, charter R-26)."""

import numpy as np
import pytest
from domain.entities import Location
from infrastructure.networkx_routing_service import NetworkXRoutingService
from infrastructure.osmnx_map_repository import ensure_travel_times
from infrastructure.rain_grid import RainGrid
from infrastructure.rain_signal import RainSignal

A = Location(6.2000, -75.5800)
B = Location(6.2000, -75.5600)
AMARILLA = RainSignal(True, 0.5, "AMARILLO", "1.0.0", "2026-10-31T15:00:00Z")


class _Fijo:
    def __init__(self, valor):
        self.valor = valor

    def signal(self, lat, lon):
        return self.valor

    def grid(self, points):
        return self.valor


def _grilla(norte, sur):
    """p = `norte` en la latitud de la avenida (6.205) y `sur` en la de la calle (6.200)."""
    lats = np.array([6.195, 6.200, 6.2025, 6.205, 6.210])
    lons = np.linspace(-75.59, -75.55, 5)
    filas = [sur, sur, (sur + norte) / 2, norte, norte]
    return RainGrid(lats, lons, np.array([[f] * 5 for f in filas]))


@pytest.fixture
def g(graph):
    ensure_travel_times(graph)
    return graph


def _servicio(grilla):
    return NetworkXRoutingService(_Fijo(AMARILLA), _Fijo(grilla))


def test_grilla_no_uniforme_dryest_distinto_de_fastest(g):
    r = _servicio(_grilla(norte=0.9, sur=0.05)).find_multiple_routes(A, B, g, "car")
    tipos = {x.route_type: x for x in r.routes}

    assert r.dryest_available
    fastest, dryest = tipos["fastest"], tipos["dryest"]
    assert len(fastest.path) == 4 and len(dryest.path) == 3  # la avenida (lluviosa) vs la calle (seca)
    assert dryest.path != fastest.path
    assert dryest.rain_exposure < 0.5 * fastest.rain_exposure  # SC-001
    assert dryest.travel_time_seconds > fastest.travel_time_seconds  # más seca, pero más lenta


def test_grilla_uniforme_dryest_coincide_y_no_se_ofrece(g):
    r = _servicio(_grilla(norte=0.6, sur=0.6)).find_multiple_routes(A, B, g, "car")
    assert r.dryest_available and "dryest" not in {x.route_type for x in r.routes}
    assert r.routes[0].rain_exposure == pytest.approx(0.6)


def test_sin_lluvia_relevante_no_se_calcula(g):
    r = _servicio(_grilla(norte=0.08, sur=0.02)).find_multiple_routes(A, B, g, "car")
    assert not r.dryest_available and "dryest" not in {x.route_type for x in r.routes}


def test_sin_grilla_no_hay_exposicion_ni_dryest(g):
    r = _servicio(None).find_multiple_routes(A, B, g, "car")
    assert not r.dryest_available and r.routes[0].rain_exposure is None


def test_sin_senal_no_se_pide_grilla(g):
    pedidas = []

    class _Grid:
        def grid(self, points):
            pedidas.append(points)

    r = NetworkXRoutingService(_Fijo(RainSignal.unavailable()), _Grid()).find_multiple_routes(A, B, g, "car")
    assert not pedidas and not r.dryest_available
