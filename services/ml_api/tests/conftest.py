import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# main.py vive en services/ml_api/ y no es un paquete instalable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main  # noqa: E402


@pytest.fixture(scope="session")
def client():
    return TestClient(main.app)


@pytest.fixture
def entrada():
    return {
        "temperatura_c": 19.0,
        "humedad_relativa_pct": 85.0,
        "cobertura_nubosa_pct": 90.0,
        "velocidad_viento_ms": 2.0,
        "hora": 15,
        "mes": 10,
        "precip_lag_1h_mm": 0.0,
    }
