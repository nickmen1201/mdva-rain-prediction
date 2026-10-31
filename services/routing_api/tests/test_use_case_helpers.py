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
