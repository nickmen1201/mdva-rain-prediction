"""API v2 contra el modelo rain_classifier real de models/ (versionado en git)."""

import time
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import main
import v2

ENTRADA = {
    "time_utc": "2026-10-28T20:00:00Z",
    "temperature_2m": 19.0,
    "relative_humidity_2m": 85.0,
    "dew_point_2m": 16.4,
    "cloud_cover": 90.0,
    "wind_speed_10m": 2.0,
    "wind_direction_10m": 180.0,
    "pressure_msl": 1013.0,
    "precipitation": 0.4,
    "cape": 300.0,
}


@pytest.fixture(scope="module")
def api():
    with TestClient(main.app) as c:  # `with` ejecuta el lifespan (carga del modelo)
        yield c


def test_health_v2_reporta_el_modelo(api):
    body = api.get("/v2/health").json()
    assert body == {
        "status": "ok",
        "ready": True,
        "model": {"name": "rain_classifier", "version": v2.MODEL_VERSION, "calibration": "none"},
    }


def test_prediccion_individual(api):
    r = api.post("/v2/predict", json=ENTRADA)
    assert r.status_code == 200
    body = r.json()
    assert 0 <= body["probability"] <= 1 and body["model_version"] == v2.MODEL_VERSION
    esperado = "ROJO" if body["probability"] > 0.7 else "AMARILLO" if body["probability"] >= 0.4 else "VERDE"
    assert body["alert_level"] == esperado


def test_mas_lluvia_pronosticada_sube_la_probabilidad(api):
    seco = api.post("/v2/predict", json=dict(ENTRADA, precipitation=0.0, cloud_cover=10.0)).json()
    humedo = api.post("/v2/predict", json=dict(ENTRADA, precipitation=5.0, cloud_cover=100.0)).json()
    assert humedo["probability"] > seco["probability"]


def test_lote_de_81_en_orden_y_rapido(api):
    registros = [dict(ENTRADA, precipitation=round(i * 0.05, 2)) for i in range(81)]
    inicio = time.perf_counter()
    r = api.post("/v2/predict/batch", json={"records": registros})
    duracion = time.perf_counter() - inicio
    assert r.status_code == 200 and len(r.json()["predictions"]) == 81
    individual = api.post("/v2/predict", json=registros[40]).json()["probability"]
    assert r.json()["predictions"][40]["probability"] == pytest.approx(individual)
    assert duracion < 1.0


@pytest.mark.parametrize("n", [0, 201])
def test_lote_vacio_o_demasiado_grande_es_422(api, n):
    r = api.post("/v2/predict/batch", json={"records": [ENTRADA] * n})
    assert r.status_code == 422 and r.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(
    "cambio,campo",
    [
        ({"relative_humidity_2m": 150.0}, "relative_humidity_2m"),
        ({"time_utc": "2026-10-28T20:00:00"}, "time_utc"),
        ({"cape": None}, "cape"),
    ],
)
def test_entrada_invalida_es_problem_details(api, cambio, campo):
    r = api.post("/v2/predict", json=dict(ENTRADA, **cambio))
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == 422 and body["instance"] == "/v2/predict"
    assert any(e["field"] == campo for e in body["errors"])


def test_campo_faltante_es_problem_details(api):
    r = api.post("/v2/predict", json={k: v for k, v in ENTRADA.items() if k != "pressure_msl"})
    assert r.status_code == 422 and any(e["field"] == "pressure_msl" for e in r.json()["errors"])


def test_v1_conserva_su_formato_de_error(api):
    r = api.post("/predecir/random_forest", json={"temperatura_c": 1})
    assert r.status_code == 422 and "detail" in r.json() and "type" not in r.json()


def test_monitoreo_v2(api, monkeypatch):
    monkeypatch.setattr(v2, "_probabilities", lambda records: [0.30])
    hace_20 = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    r = api.post(
        "/v2/monitor/trip", json={"probability_start": 0.0, "weather_timestamp_utc": hace_20, "current": ENTRADA}
    )
    body = r.json()
    assert r.status_code == 200
    assert body["change_level"] == "CRITICO" and body["stale_data"] is True and body["latency_minutes"] in (19, 20)
    assert body["delta"] == pytest.approx(0.30)


def test_monitoreo_v2_exige_zona_horaria(api):
    r = api.post(
        "/v2/monitor/trip",
        json={"probability_start": 0.1, "weather_timestamp_utc": "2026-10-28T10:00:00", "current": ENTRADA},
    )
    assert r.status_code == 422 and any(e["field"] == "weather_timestamp_utc" for e in r.json()["errors"])


def test_error_interno_no_expone_detalles(api, monkeypatch):
    def falla(records):
        raise RuntimeError("secreto interno")

    monkeypatch.setattr(v2, "_probabilities", falla)
    cliente = TestClient(main.app, raise_server_exceptions=False)
    with cliente:
        r = cliente.post("/v2/predict", json=ENTRADA)
    assert r.status_code == 500 and "secreto" not in r.text and r.json()["title"] == "Error interno"


def test_modelo_incompatible_impide_el_arranque(monkeypatch):
    monkeypatch.setattr(v2, "MODEL_VERSION", "9.9.9")
    with pytest.raises(FileNotFoundError):
        with TestClient(main.app):
            pass
