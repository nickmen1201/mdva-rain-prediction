"""El contrato OpenAPI v2 es válido y el servicio lo cumple (constitución IV)."""

from pathlib import Path

import pytest
import yaml
from openapi_spec_validator import validate

import main

CONTRATO = Path(__file__).resolve().parents[3] / "specs" / "006-ml-api-v2" / "contracts" / "openapi-v2.yaml"


@pytest.fixture(scope="module")
def contrato():
    return yaml.safe_load(CONTRATO.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def servicio():
    return main.app.openapi()


def _resolver(spec, schema):
    while "$ref" in schema:
        nombre = schema["$ref"].split("/")[-1]
        schema = spec["components"]["schemas"][nombre]
    return schema


def _rutas_v2(spec):
    return {(ruta, metodo) for ruta, ops in spec["paths"].items() if ruta.startswith("/v2") for metodo in ops}


def test_contrato_es_openapi_valido(contrato):
    validate(contrato)


def test_rutas_y_metodos_coinciden(contrato, servicio):
    assert _rutas_v2(servicio) == _rutas_v2(contrato)


def test_campos_de_entrada_y_salida_coinciden(contrato, servicio):
    for ruta, metodo in _rutas_v2(contrato):
        op_c, op_s = contrato["paths"][ruta][metodo], servicio["paths"][ruta][metodo]
        if "requestBody" in op_c:
            req_c = _resolver(contrato, op_c["requestBody"]["content"]["application/json"]["schema"])
            req_s = _resolver(servicio, op_s["requestBody"]["content"]["application/json"]["schema"])
            assert set(req_c["required"]) == set(req_s["required"]), ruta
            assert set(req_c["properties"]) == set(req_s["properties"]), ruta
        res_c = _resolver(contrato, op_c["responses"]["200"]["content"]["application/json"]["schema"])
        res_s = _resolver(servicio, op_s["responses"]["200"]["content"]["application/json"]["schema"])
        assert set(res_c["properties"]) == set(res_s["properties"]), ruta
        assert set(res_c["required"]) == set(res_s["required"]), ruta


def test_rangos_de_entrada_coinciden(contrato, servicio):
    entrada_c = contrato["components"]["schemas"]["PredictionInput"]["properties"]
    entrada_s = servicio["components"]["schemas"]["PredictionInput"]["properties"]
    for campo, prop in entrada_c.items():
        if "minimum" in prop:
            assert (entrada_s[campo]["minimum"], entrada_s[campo]["maximum"]) == (prop["minimum"], prop["maximum"])
