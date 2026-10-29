"""Tests de caracterización: congelan el comportamiento observable del servicio ML (spec 002, US4)."""

import pytest

MODELOS = ["regresion_logistica", "random_forest"]


def test_health_reporta_ambos_modelos(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "modelos_cargados": MODELOS}


def test_raiz_reporta_servicio_y_version(client):
    body = client.get("/").json()
    assert body["servicio"] == "MDVA Predicción de Lluvia"
    assert body["version"] == "1.0.0"
    assert body["modelos"] == MODELOS


@pytest.mark.parametrize("modelo", MODELOS)
def test_prediccion_por_modelo(client, entrada, modelo):
    resp = client.post(f"/predecir/{modelo}", json=entrada)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"modelo", "llueve", "probabilidad_lluvia", "etiqueta"}
    assert body["modelo"] == modelo
    assert 0.0 <= body["probabilidad_lluvia"] <= 1.0
    assert body["etiqueta"] == ("llueve" if body["llueve"] else "no llueve")


def test_prediccion_ambos_devuelve_los_dos_en_orden(client, entrada):
    resp = client.post("/predecir/ambos", json=entrada)
    assert resp.status_code == 200
    assert [p["modelo"] for p in resp.json()] == MODELOS


def test_lag_es_opcional_con_default_cero(client, entrada):
    sin_lag = {k: v for k, v in entrada.items() if k != "precip_lag_1h_mm"}
    a = client.post("/predecir/random_forest", json=sin_lag).json()
    b = client.post("/predecir/random_forest", json=entrada).json()
    assert a == b


def test_modelo_desconocido_es_422(client, entrada):
    assert client.post("/predecir/xgboost", json=entrada).status_code == 422


@pytest.mark.parametrize(
    "campo,valor",
    [("hora", 24), ("hora", -1), ("mes", 0), ("mes", 13), ("precip_lag_1h_mm", -0.1)],
)
def test_entrada_fuera_de_rango_es_422(client, entrada, campo, valor):
    entrada[campo] = valor
    assert client.post("/predecir/random_forest", json=entrada).status_code == 422


def test_campo_obligatorio_faltante_es_422(client, entrada):
    del entrada["temperatura_c"]
    assert client.post("/predecir/ambos", json=entrada).status_code == 422
