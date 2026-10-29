"""Funciones puras del caso de uso de rutas (sin grafo OSM ni red)."""

import pytest
from application.use_cases import FindBestRouteUseCase
from domain.entities import Location


@pytest.fixture
def use_case():
    # Los helpers no usan el repositorio ni el servicio de rutas
    return FindBestRouteUseCase.__new__(FindBestRouteUseCase)


def test_polyline_ejemplo_oficial_de_google(use_case):
    path = [
        {"latitude": 38.5, "longitude": -120.2},
        {"latitude": 40.7, "longitude": -120.95},
        {"latitude": 43.252, "longitude": -126.453},
    ]
    assert use_case._encode_polyline(path) == "_p~iF~ps|U_ulLnnqC_mqNvxq`@"


def test_polyline_acepta_entidades_location(use_case):
    dicts = [{"latitude": 6.2502, "longitude": -75.5684}, {"latitude": 6.2088, "longitude": -75.5672}]
    locations = [Location(latitude=d["latitude"], longitude=d["longitude"]) for d in dicts]
    assert use_case._encode_polyline(locations) == use_case._encode_polyline(dicts)


def test_polyline_vacia(use_case):
    assert use_case._encode_polyline([]) == ""


def test_haversine_parque_berrio_a_el_poblado():
    distancia = FindBestRouteUseCase._haversine(6.2502, -75.5684, 6.2088, -75.5672)
    assert distancia == pytest.approx(4605, abs=5)


def test_haversine_mismo_punto_es_cero():
    assert FindBestRouteUseCase._haversine(6.25, -75.57, 6.25, -75.57) == 0


@pytest.mark.parametrize(
    "lat2,lon2,esperado",
    [(1, 0, 0), (0, 1, 90), (-1, 0, 180), (0, -1, 270)],
)
def test_bearing_puntos_cardinales(lat2, lon2, esperado):
    assert FindBestRouteUseCase._bearing(0, 0, lat2, lon2) == pytest.approx(esperado)


@pytest.mark.parametrize(
    "bearing,direccion",
    [
        (0, "norte"),
        (22.4, "norte"),
        (22.5, "noreste"),
        (90, "este"),
        (180, "sur"),
        (270, "oeste"),
        (337.5, "norte"),
        (359.9, "norte"),
    ],
)
def test_bearing_a_direccion(bearing, direccion):
    assert FindBestRouteUseCase._bearing_to_direction(bearing) == direccion
