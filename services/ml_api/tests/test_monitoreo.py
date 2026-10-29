"""Tabla de reglas de monitoreo de trayecto (charter RF-17), congelada antes de la spec 006.

La probabilidad actual se fija con monkeypatch para que las reglas no dependan del modelo.
"""

from datetime import datetime, timedelta, timezone

import main
import pytest


def _iso_hace(minutos):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutos)).isoformat()


@pytest.fixture
def con_probabilidad(monkeypatch):
    def fijar(prob):
        def falso_predecir(nombre_modelo, entrada):
            return main.ResultadoPrediccion(
                modelo=nombre_modelo, llueve=prob >= 0.5, probabilidad_lluvia=prob, etiqueta="x"
            )

        monkeypatch.setattr(main, "predecir", falso_predecir)

    return fijar


def _monitorear(client, entrada, prob_inicio, ts_weather):
    payload = {
        "snapshot": {
            "probabilidad_rf_inicio": prob_inicio,
            "temperatura_inicio": 20.0,
            "timestamp_snapshot": ts_weather,
            "timestamp_dato_weather": ts_weather,
        },
        "condiciones_actuales": entrada,
    }
    resp = client.post("/monitorear/trayecto", json=payload)
    assert resp.status_code == 200
    return resp.json()


@pytest.mark.parametrize(
    "inicio,actual,latencia_min,nivel",
    [
        (0.00, 0.05, 0, "ESTABLE"),  # delta < 0.10
        (0.00, 0.10, 0, "MODERADO"),  # borde inferior incluido
        (0.00, 0.25, 0, "MODERADO"),  # borde superior incluido
        (0.00, 0.30, 0, "SIGNIFICATIVO"),  # delta > 0.25
        (0.50, 0.20, 0, "ESTABLE"),  # delta negativo no alerta
        (0.00, 0.05, 20, "MODERADO"),  # latencia > 15 min sube un nivel
        (0.00, 0.10, 20, "SIGNIFICATIVO"),
        (0.00, 0.30, 20, "CRITICO"),
        (0.00, 0.05, 15, "ESTABLE"),  # 15 min exactos no cuenta como latencia
        (0.80, 0.86, 0, "CRITICO"),  # prob actual > 0.85 prevalece
        (0.00, 0.85, 0, "SIGNIFICATIVO"),  # 0.85 exacto no es CRITICO
    ],
)
def test_tabla_de_reglas(client, entrada, con_probabilidad, inicio, actual, latencia_min, nivel):
    con_probabilidad(actual)
    body = _monitorear(client, entrada, inicio, _iso_hace(latencia_min))
    assert body["nivel_cambio"] == nivel
    assert body["dato_con_latencia"] == (latencia_min > 15)
    assert body["probabilidad_rf_actual"] == actual
    assert body["delta_probabilidad"] == pytest.approx(actual - inicio)


def test_minutos_de_latencia_reportados(client, entrada, con_probabilidad):
    con_probabilidad(0.1)
    body = _monitorear(client, entrada, 0.1, _iso_hace(42))
    assert body["minutos_latencia"] in (41, 42)


def test_timestamp_futuro_no_da_latencia_negativa(client, entrada, con_probabilidad):
    con_probabilidad(0.1)
    body = _monitorear(client, entrada, 0.1, _iso_hace(-30))
    assert body["minutos_latencia"] == 0


def test_timestamp_con_z(client, entrada, con_probabilidad):
    con_probabilidad(0.1)
    ts = (datetime.now(timezone.utc) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = _monitorear(client, entrada, 0.1, ts)
    assert body["dato_con_latencia"] is True


@pytest.mark.parametrize("ts", ["no-es-fecha", "2026-10-28T10:00:00"])
def test_timestamp_invalido_o_sin_zona_cae_en_latencia_cero(client, entrada, con_probabilidad, ts):
    # Comportamiento actual (se revisa en la spec 006): un timestamp sin zona horaria
    # no se puede restar de "ahora" en UTC y se trata en silencio como latencia 0.
    con_probabilidad(0.1)
    body = _monitorear(client, entrada, 0.1, ts)
    assert body["minutos_latencia"] == 0
    assert body["dato_con_latencia"] is False
