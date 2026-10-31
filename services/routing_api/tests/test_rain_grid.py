"""Grilla espacial de lluvia: malla, interpolación y fallos sin relleno (spec 010)."""

from datetime import UTC, datetime

import numpy as np
import pytest
import requests
from infrastructure.rain_grid import MIN_SPAN_DEG, N, RainGrid, RainGridClient, grid_axes
from infrastructure.rain_signal import VARIABLES

AHORA = datetime(2026, 10, 31, 15, 5, tzinfo=UTC)


def _ubicacion():
    horas = [f"2026-10-31T{h:02d}:00" for h in range(24)]
    return {"hourly_units": dict(VARIABLES), "hourly": {"time": horas, **{v: [1.0] * 24 for v in VARIABLES}}}


class _Resp:
    def __init__(self, body, status=200):
        self._body, self.status_code = body, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def json(self):
        return self._body


class _Session:
    def __init__(self, n_ubicaciones=N * N, probs=None):
        self.n, self.probs = n_ubicaciones, probs
        self.gets, self.posts = [], []

    def get(self, url, params=None, timeout=None):
        self.gets.append(params)
        return _Resp([_ubicacion() for _ in range(self.n)])

    def post(self, url, json=None, timeout=None):
        self.posts.append(json)
        probs = self.probs if self.probs is not None else [i / 100 for i in range(len(json["records"]))]
        return _Resp({"model_version": "1.0.0", "predictions": [{"probability": p} for p in probs]})


def _client(s):
    return RainGridClient("http://ml:8081", session=s, now_utc=lambda: AHORA)


def test_ejes_con_margen_y_lado_minimo():
    lats, lons = grid_axes([(6.20, -75.58), (6.20, -75.56)])
    assert len(lats) == N and len(lons) == N
    assert lats[-1] - lats[0] == pytest.approx(MIN_SPAN_DEG, abs=1e-4)  # misma latitud → lado mínimo
    assert lons[0] == pytest.approx(-75.59) and lons[-1] == pytest.approx(-75.55)


def test_una_consulta_de_clima_y_una_de_prediccion_para_25_puntos():
    s = _Session()
    g = _client(s).grid([(6.20, -75.58), (6.25, -75.55)])

    assert len(s.gets) == 1 and len(s.posts) == 1
    assert len(s.gets[0]["latitude"].split(",")) == N * N
    assert len(s.posts[0]["records"]) == N * N
    assert s.posts[0]["records"][0]["time_utc"] == "2026-10-31T15:00:00Z"
    assert g.p.shape == (N, N) and g.p[0, 1] == pytest.approx(0.01)  # fila = latitud, columna = longitud
    assert g.model_version == "1.0.0"


def test_cache_por_caja():
    s = _Session()
    c = _client(s)
    c.grid([(6.20, -75.58), (6.25, -75.55)])
    c.grid([(6.201, -75.581), (6.249, -75.551)])
    assert len(s.posts) == 1


@pytest.mark.parametrize("session", [_Session(n_ubicaciones=24), _Session(probs=[0.5] * 3)])
def test_grilla_incompleta_no_disponible(session):
    assert _client(session).grid([(6.20, -75.58), (6.25, -75.55)]) is None


def test_interpolacion_bilineal_y_bordes():
    lats = np.array([6.0, 6.1, 6.2, 6.3, 6.4])
    lons = np.array([-75.6, -75.5, -75.4, -75.3, -75.2])
    p = np.add.outer(np.arange(5) * 0.1, np.arange(5) * 0.01)  # p = 0.1·i + 0.01·j
    g = RainGrid(lats, lons, p)

    assert g.at(6.0, -75.6) == pytest.approx(0.0)
    assert g.at(6.15, -75.45) == pytest.approx(0.15 + 0.015)  # lineal en ambos ejes → exacto
    assert g.at(7.0, -76.0) == pytest.approx(g.at(6.4, -75.6))  # fuera de la malla: borde
    assert g.max_probability == pytest.approx(0.44)
