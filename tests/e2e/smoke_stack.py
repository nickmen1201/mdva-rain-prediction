"""Smoke test de punta a punta del stack de desarrollo de MDVA.

Verifica health de los tres backends, autenticación, predicción ML, ruta del
routing service y los endpoints de viaje y clima del Backend. Imprime un JSON
con solo datos deterministas (códigos HTTP y forma de la respuesta) para poder
comparar corridas con `diff` antes y después de un cambio.

Uso:
    python tests/e2e/smoke_stack.py > smoke.json

Variables opcionales: ML_URL, ROUTING_URL, BACKEND_URL.
"""

import json
import os
import sys
import urllib.error
import urllib.request
import uuid

ML_URL = os.environ.get("ML_URL", "http://localhost:8081")
ROUTING_URL = os.environ.get("ROUTING_URL", "http://localhost:8000")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8080")

# Parque Berrío → El Poblado (Medellín)
ORIGEN = {"lat": 6.2502, "lng": -75.5684}
DESTINO = {"lat": 6.2088, "lng": -75.5672}

ML_PAYLOAD = {
    "temperatura_c": 19.0,
    "humedad_relativa_pct": 85.0,
    "cobertura_nubosa_pct": 90.0,
    "velocidad_viento_ms": 2.0,
    "hora": 15,
    "mes": 10,
    "precip_lag_1h_mm": 0.0,
}


def request(method, url, body=None, token=None, timeout=180):
    """Devuelve (status, json_o_None). Nunca lanza por códigos HTTP de error."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read()
        status = e.code
    except (urllib.error.URLError, TimeoutError) as e:
        return None, {"error": type(e).__name__}
    try:
        return status, json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return status, None


def main():
    results = {}

    for name, url in [
        ("ml_health", f"{ML_URL}/health"),
        ("routing_health", f"{ROUTING_URL}/health"),
        ("backend_health", f"{BACKEND_URL}/api/health"),
    ]:
        status, _ = request("GET", url)
        results[name] = {"status": status}

    status, body = request("POST", f"{ML_URL}/predecir/ambos", ML_PAYLOAD)
    modelos = sorted(p.get("modelo") for p in body) if isinstance(body, list) else None
    results["ml_predecir_ambos"] = {"status": status, "modelos": modelos}

    route_req = {
        "origin": {"latitude": ORIGEN["lat"], "longitude": ORIGEN["lng"]},
        "destination": {"latitude": DESTINO["lat"], "longitude": DESTINO["lng"]},
        "vehicle_type": "car",
    }
    status, body = request("POST", f"{ROUTING_URL}/api/v1/route", route_req)
    has_routes = bool(isinstance(body, dict) and body.get("options"))
    results["routing_route"] = {"status": status, "has_routes": has_routes}

    username = f"smoke_{uuid.uuid4().hex[:8]}"
    password = "Smoke12345!"
    status, _ = request(
        "POST",
        f"{BACKEND_URL}/auth/register",
        {"nombre": "Smoke", "username": username, "email": f"{username}@test.co", "password": password},
    )
    results["auth_register"] = {"status": status}

    status, body = request("POST", f"{BACKEND_URL}/auth/login", {"username": username, "password": password})
    token = body.get("token") if isinstance(body, dict) else None
    results["auth_login"] = {"status": status, "has_token": bool(token)}

    status, body = request("GET", f"{BACKEND_URL}/api/locations/municipalities", token=token)
    results["locations_municipalities"] = {"status": status, "non_empty": bool(body)}

    status, _ = request(
        "GET",
        f"{BACKEND_URL}/api/weather/current?latitude={ORIGEN['lat']}&longitude={ORIGEN['lng']}",
        token=token,
    )
    results["weather_current"] = {"status": status}

    status, _ = request(
        "GET",
        f"{BACKEND_URL}/api/weather/forecast?latitude={ORIGEN['lat']}&longitude={ORIGEN['lng']}",
        token=token,
    )
    results["weather_forecast"] = {"status": status}

    trip = {
        "tipoVehiculo": "CARRO",
        "origen": {**ORIGEN, "displayName": "Parque Berrio"},
        "destino": {**DESTINO, "displayName": "El Poblado"},
    }
    status, _ = request("POST", f"{BACKEND_URL}/api/viajes/planificar", trip, token=token)
    results["viajes_planificar"] = {"status": status}

    json.dump(results, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
