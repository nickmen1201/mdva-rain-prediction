"""Recorrido de la interfaz con un navegador real (spec 011, SC-002): sin ninguna API key.

login → mapa de la ciudad (heatmap + leyenda) → planificar con búsqueda de direcciones (Nominatim)
→ resultado con la ruta → navegación en ruta. Guarda capturas en `reports/figures/ui/`.

Requiere el stack arriba (`make up`) y Chromium de Playwright:
    make ui-smoke
"""

import json
import os
import sys
import urllib.request
import uuid
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:8090")
BACKEND = os.environ.get("BACKEND_URL", "http://localhost:8080")
OUT = Path(__file__).resolve().parents[2] / "reports" / "figures" / "ui"


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    usuario = f"ui_{uuid.uuid4().hex[:8]}"
    _post(
        f"{BACKEND}/auth/register",
        {"nombre": "UI", "username": usuario, "email": f"{usuario}@test.co", "password": "Smoke12345!"},
    )
    sesion = _post(f"{BACKEND}/auth/login", {"username": usuario, "password": "Smoke12345!"})
    resultados = {}
    errores_consola = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": 430, "height": 900},
            geolocation={"latitude": 6.2707, "longitude": -75.5659},
            permissions=["geolocation"],
        )
        page.on("console", lambda m: errores_consola.append(m.text) if m.type == "error" else None)
        page.goto(FRONTEND + "/login")
        page.evaluate(
            "([t, u]) => { localStorage.setItem('token', t); localStorage.setItem('username', u); }",
            [sesion["token"], usuario],
        )

        # 1. Mapa de la ciudad: teselas, atribución, heatmap y leyenda
        page.goto(FRONTEND + "/")
        page.wait_for_selector(".maplibregl-canvas", timeout=30_000)
        page.wait_for_selector(".rain-legend", timeout=60_000)
        page.wait_for_timeout(2500)
        resultados["mapa_ciudad"] = {
            "canvas": page.locator(".maplibregl-canvas").count() > 0,
            "atribucion_osm": "OpenStreetMap" in page.locator(".maplibregl-ctrl-attrib").inner_text(),
            "leyenda": page.locator(".rain-legend").is_visible(),
        }
        page.screenshot(path=OUT / "1-mapa-ciudad.png")

        # 2. Planificar: búsqueda de origen y destino (Enter), sin autocompletado
        page.goto(FRONTEND + "/planificar")
        page.wait_for_selector(".maplibregl-canvas", timeout=30_000)
        busquedas = page.locator(".place-search input")
        busquedas.nth(0).fill("Parque Explora")
        busquedas.nth(0).press("Enter")
        page.wait_for_selector(".place-results button", timeout=30_000)
        page.locator(".place-results button").first.click()
        busquedas.nth(1).fill("Estadio Atanasio Girardot")
        busquedas.nth(1).press("Enter")
        page.wait_for_selector(".place-results button", timeout=30_000)
        page.locator(".place-results button").first.click()
        page.wait_for_timeout(1500)
        page.screenshot(path=OUT / "2-planificar.png", full_page=True)
        with page.expect_response("**/api/viajes/planificar") as respuesta:
            page.get_by_role("button", name="Planificar viaje").click()
        viaje = respuesta.value.json()
        page.evaluate("o => sessionStorage.setItem('mdva-last-origin', JSON.stringify(o))", viaje["origen"])
        page.wait_for_url("**/viaje/*", timeout=60_000)

        # 3. Resultado con la ruta dibujada
        page.wait_for_selector(".maplibregl-canvas", timeout=30_000)
        page.wait_for_timeout(2500)
        resultados["resultado"] = {"url": page.url, "marcadores": page.locator(".map-dot").count()}
        page.screenshot(path=OUT / "3-resultado.png", full_page=True)

        # 4. Navegación en ruta (el GPS simulado está en el origen: Parque Explora)
        page.get_by_role("button", name="Iniciar navegación").click()
        page.wait_for_url("**/en-ruta", timeout=60_000)
        page.wait_for_selector(".maplibregl-canvas", timeout=30_000)
        page.wait_for_timeout(5000)
        resultados["en_ruta"] = {"canvas": page.locator(".maplibregl-canvas").count() > 0}
        page.screenshot(path=OUT / "4-en-ruta.png")
        browser.close()

    resultados["errores_consola"] = errores_consola[:10]
    json.dump(resultados, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    ok = (
        all(resultados["mapa_ciudad"].values())
        and resultados["resultado"]["marcadores"] >= 2
        and resultados["en_ruta"]["canvas"]
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
