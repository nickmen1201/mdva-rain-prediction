"""Tabla RF-17 sobre la función pura (la misma tabla que tests/test_monitoreo.py usa contra v1)."""

from datetime import datetime, timedelta, timezone

import pytest

import monitoring

TABLA = [
    (0.00, 0.05, 0, "ESTABLE"),
    (0.00, 0.10, 0, "MODERADO"),
    (0.00, 0.25, 0, "MODERADO"),
    (0.00, 0.30, 0, "SIGNIFICATIVO"),
    (0.50, 0.20, 0, "ESTABLE"),
    (0.00, 0.05, 20, "MODERADO"),
    (0.00, 0.10, 20, "SIGNIFICATIVO"),
    (0.00, 0.30, 20, "CRITICO"),
    (0.00, 0.05, 15, "ESTABLE"),
    (0.80, 0.86, 0, "CRITICO"),
    (0.00, 0.85, 0, "SIGNIFICATIVO"),
    (0.00, 0.90, 20, "CRITICO"),
]


@pytest.mark.parametrize("inicio,actual,latencia,nivel", TABLA)
def test_tabla_rf17(inicio, actual, latencia, nivel):
    assert monitoring.change_level(inicio, actual, latencia) == nivel


def test_latencia_nunca_negativa_y_en_minutos_enteros():
    ahora = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)
    assert monitoring.latency_minutes(ahora - timedelta(minutes=42, seconds=30), ahora) == 42
    assert monitoring.latency_minutes(ahora + timedelta(minutes=10), ahora) == 0


def test_latencia_con_zonas_distintas():
    bogota = timezone(timedelta(hours=-5))
    ahora = datetime(2026, 10, 28, 20, 0, tzinfo=timezone.utc)
    assert monitoring.latency_minutes(datetime(2026, 10, 28, 14, 30, tzinfo=bogota), ahora) == 30
