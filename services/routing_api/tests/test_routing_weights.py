"""Costos por arista: tiempo real, distancia, bicicleta y factor de lluvia (spec 009, R-30)."""

import pytest
from conftest import IDS
from domain.entities import Location
from infrastructure.networkx_routing_service import BIKE_MAX_KPH, NetworkXRoutingService
from infrastructure.osmnx_map_repository import ensure_travel_times
from infrastructure.rain_signal import RainSignal

A = Location(6.2000, -75.5800)
B = Location(6.2000, -75.5600)


class _Signal:
    def __init__(self, signal):
        self.s = signal

    def signal(self, lat, lon):
        return self.s


@pytest.fixture
def g(graph):
    assert ensure_travel_times(graph) is True
    assert ensure_travel_times(graph) is False  # idempotente: ya tiene tiempos
    return graph


def test_velocidades_desde_maxspeed(g):
    data = g.get_edge_data(IDS["A"], IDS["D"])[0]
    assert data["speed_kph"] == pytest.approx(80)
    assert data["travel_time"] == pytest.approx(data["length"] / (80 / 3.6), rel=1e-2)


def test_fastest_prefiere_la_avenida_y_shortest_la_calle(g):
    r = NetworkXRoutingService().find_multiple_routes(A, B, g, "car")
    por_tipo = {x.route_type: x for x in r.routes}

    fastest, shortest = por_tipo["fastest"], por_tipo["shortest"]
    assert len(fastest.path) == 4 and len(shortest.path) == 3  # A-D-E-B vs A-C-B
    assert fastest.travel_time_seconds < shortest.travel_time_seconds
    assert shortest.distance_meters < fastest.distance_meters
    assert fastest.travel_time_seconds == pytest.approx(sum(s.time_s for s in fastest.segments), abs=0.01)
    assert r.signal.available is False and fastest.rain_factor == 1.0  # sin señal: sin penalización


def test_bicicleta_limitada_a_15_kph_elige_la_calle(g):
    r = NetworkXRoutingService().find_multiple_routes(A, B, g, "bike")
    fastest = r.routes[0]
    assert len(fastest.path) == 3  # a 15 km/h la avenida ya no compensa la distancia
    for s in fastest.segments:
        assert s.length_m / s.time_s * 3.6 <= BIKE_MAX_KPH + 1e-9


def test_factor_rf10_multiplica_tiempos_sin_cambiar_el_camino(g):
    sin = NetworkXRoutingService().find_multiple_routes(A, B, g, "car").routes[0]
    roja = RainSignal(True, 0.8, "ROJO", "1.0.0", "2026-10-31T15:00:00Z")
    con = NetworkXRoutingService(_Signal(roja)).find_multiple_routes(A, B, g, "car")

    assert con.routes[0].path == sin.path
    assert con.routes[0].travel_time_seconds == pytest.approx(sin.travel_time_seconds * 1.35, abs=0.02)
    assert con.signal.probability == 0.8


def test_pasos_por_via_con_nombre(g):
    from application.navigation import build_steps

    fastest = NetworkXRoutingService().find_multiple_routes(A, B, g, "car").routes[0]
    pasos = build_steps(fastest.segments)
    assert len(pasos) == 1 and "Avenida Oriental" in pasos[0].instruction
    assert pasos[0].duration_s == pytest.approx(fastest.travel_time_seconds, abs=0.01)
