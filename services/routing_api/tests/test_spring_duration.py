"""`/route/spring` devuelve la duración base: el ajuste por lluvia es del Backend (spec 008, H-27)."""

import pytest
from application.dtos import Coordinate, SpringRouteRequest
from application.use_cases import FindBestRouteUseCase
from infrastructure.networkx_routing_service import NetworkXRoutingService
from infrastructure.osmnx_map_repository import ensure_travel_times
from infrastructure.rain_signal import RainSignal

ROJA = RainSignal(True, 0.9, "ROJO", "1.0.0", "2026-10-31T15:00:00Z")


class _Repo:
    def __init__(self, graph):
        ensure_travel_times(graph)
        self.graph = graph

    def load_graph(self):
        return self.graph


class _Signal:
    def __init__(self, s):
        self.s = s

    def signal(self, lat, lon):
        return self.s


def _req(**kw):
    return SpringRouteRequest(
        origen=Coordinate(latitude=6.2000, longitude=-75.5800),
        destino=Coordinate(latitude=6.2000, longitude=-75.5600),
        **kw,
    )


def test_duracion_base_sin_factor_de_alerta(graph):
    base = FindBestRouteUseCase(_Repo(graph), NetworkXRoutingService()).execute_spring(_req())
    roja = FindBestRouteUseCase(_Repo(graph), NetworkXRoutingService(_Signal(ROJA))).execute_spring(_req())

    assert roja.duracionSegundos == base.duracionSegundos  # el ROJO no cambia la duración base
    assert roja.rain_factor == 1.35 and roja.alerta_nivel == "ROJO" and roja.rain_probability == 0.9
    assert base.clima_disponible is False and base.rain_probability is None and base.alerta_nivel is None
    assert sum(p.duracionSegundos for p in base.pasos) == pytest.approx(base.duracionSegundos, abs=len(base.pasos))
    assert base.alternativas[0].route_type == "shortest"
    assert base.alternativas[0].duracionSegundos > base.duracionSegundos


def test_paradas_unen_tramos_en_orden(graph):
    r = FindBestRouteUseCase(_Repo(graph), NetworkXRoutingService()).execute_spring(
        _req(paradas=[Coordinate(latitude=6.2000, longitude=-75.5700)])
    )
    assert r.distanciaMetros == pytest.approx(2212, abs=5)  # A → C → B por la calle
    assert r.alternativas is None and r.overviewPolyline


def test_metrics_y_multi_usan_una_sola_senal(graph):
    llamadas = []

    class _Contador(_Signal):
        def signal(self, lat, lon):
            llamadas.append((lat, lon))
            return ROJA

    uc = FindBestRouteUseCase(_Repo(graph), NetworkXRoutingService(_Contador(ROJA)))
    from application.dtos import MultiStopRouteRequest

    multi = uc.execute_multi_stop(
        MultiStopRouteRequest(
            waypoints=[
                Coordinate(latitude=6.2000, longitude=-75.5800),
                Coordinate(latitude=6.2000, longitude=-75.5700),
                Coordinate(latitude=6.2000, longitude=-75.5600),
            ]
        )
    )
    assert len(multi.legs) == 2 and len(llamadas) == 1 and multi.alerta_nivel == "ROJO"
    m = uc.metrics(_req())
    assert m.rain_probability == 0.9 and m.time_utc == "2026-10-31T15:00:00Z"
