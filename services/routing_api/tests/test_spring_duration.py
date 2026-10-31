"""`/route/spring` devuelve la duración base: el ajuste por lluvia es del Backend (spec 008, H-27)."""

from application.dtos import Coordinate, SpringRouteRequest
from application.use_cases import FindBestRouteUseCase
from domain.entities import Location, Route


class _Repo:
    def load_graph(self):
        return object()


class _Routing:
    def __init__(self, routes):
        self.routes = routes

    def find_multiple_routes(self, origin, destination, graph, vehicle_type="car"):
        return self.routes


def _route(route_type, seconds, prob):
    path = [Location(6.2502, -75.5684), Location(6.2300, -75.5700), Location(6.2088, -75.5672)]
    return Route(
        distance_meters=6000.0,
        travel_time_seconds=seconds,
        path=path,
        route_type=route_type,
        mdva_probabilidad_rf=prob,
    )


def test_duracion_base_sin_factor_de_alerta():
    routing = _Routing([_route("fastest", 600.0, 0.9), _route("shortest", 650.0, 0.9)])
    use_case = FindBestRouteUseCase(_Repo(), routing)
    request = SpringRouteRequest(
        origen=Coordinate(latitude=6.2502, longitude=-75.5684),
        destino=Coordinate(latitude=6.2088, longitude=-75.5672),
    )

    response = use_case.execute_spring(request)

    assert response.duracionSegundos == 600
    assert response.alternativas[0].duracionSegundos == 650
