"""Pasos de navegación agrupados por vía (spec 009)."""

import pytest
from application.navigation import Segment, bearing, build_steps, turn, via_label


def _seg(a, b, name, length=100.0, time=10.0):
    return Segment(start=a, end=b, length_m=length, time_s=time, name=name, highway="residential")


def test_agrupa_aristas_de_la_misma_via_y_suma_tiempos():
    segs = [
        _seg((6.200, -75.580), (6.200, -75.579), "Calle 10"),
        _seg((6.200, -75.579), (6.200, -75.578), "Calle 10"),
        _seg((6.200, -75.578), (6.201, -75.578), "Carrera 43A", length=250, time=20),
    ]
    steps = build_steps(segs)

    assert [s.distance_m for s in steps] == [200, 250]
    assert sum(s.duration_s for s in steps) == sum(s.time_s for s in segs)
    assert steps[0].instruction == "Sal por Calle 10 durante 200 m"
    # De rumbo este a rumbo norte: giro a la izquierda
    assert steps[1].instruction == "Gira a la izquierda por Carrera 43A durante 250 m"
    assert steps[0].start == (6.200, -75.580) and steps[1].end == (6.201, -75.578)


def test_ruta_vacia():
    assert build_steps([]) == []


@pytest.mark.parametrize(
    ("prev", "nxt", "esperado"),
    [
        (90, 180, "Gira a la derecha"),
        (90, 0, "Gira a la izquierda"),
        (90, 100, "Continúa"),
        (350, 20, "Continúa"),
        (10, 300, "Gira a la izquierda"),
    ],
)
def test_giros(prev, nxt, esperado):
    assert turn(prev, nxt) == esperado


def test_rumbos():
    assert bearing((6.2, -75.58), (6.3, -75.58)) == pytest.approx(0, abs=0.01)
    assert bearing((6.2, -75.58), (6.2, -75.50)) == pytest.approx(90, abs=0.01)


def test_nombre_de_via():
    assert via_label("Calle 10", "residential") == "Calle 10"
    assert via_label(["Avenida 80", "Calle 30"], "primary") == "Avenida 80"
    assert via_label(None, "primary") == "vía primary"
    assert via_label(None, ["tertiary", "residential"]) == "vía tertiary"
    assert via_label(None, None) is None
    assert build_steps([_seg((6.2, -75.58), (6.2, -75.57), None, length=1500)])[0].instruction == (
        "Sal por la vía durante 1.5 km"
    )
