"""App: healthcheck y CORS limitado a orígenes configurados (spec 009, R-33)."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app_con(monkeypatch):
    def crear(origenes):
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", origenes)
        import main

        return TestClient(importlib.reload(main).app)

    return crear


def test_health(app_con):
    assert app_con("").get("/health").json() == {"status": "ok", "service": "enrutamiento-ambiental"}


def test_cors_solo_para_origenes_configurados(app_con):
    c = app_con("http://localhost:8090, https://mdva.example.co")
    ok = c.options("/health", headers={"Origin": "http://localhost:8090", "Access-Control-Request-Method": "GET"})
    otro = c.options("/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:8090"
    assert "access-control-allow-origin" not in otro.headers


def test_sin_origenes_no_hay_cors(app_con):
    r = app_con("").get("/health", headers={"Origin": "http://localhost:8090"})
    assert "access-control-allow-origin" not in r.headers
