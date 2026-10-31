"""
MDVA — Monitoreo de Variables Ambientales
Servicio FastAPI de predicción de lluvia: solo el modelo evaluado `rain_classifier` (API v2).

Los endpoints v1 (`/predecir/*`, `/monitorear/trayecto`) y sus modelos heredados se retiraron en la
spec 009: ningún servicio los usaba y sus modelos no tenían evaluación temporal (charter H-07).
"""

from fastapi import FastAPI

import v2

app = FastAPI(
    title="MDVA Predicción de Lluvia",
    description="Probabilidad de lluvia por hora para el Valle de Aburrá (modelo `rain_classifier`).",
    version="2.0.0",
    lifespan=v2.lifespan,
)
app.include_router(v2.router)
v2.install_error_handlers(app)


@app.get("/", tags=["Info"])
def raiz():
    m = v2.current_model_info()
    return {"servicio": "MDVA Predicción de Lluvia", "version": app.version, "modelo": m}


@app.get("/health", tags=["Info"])
def health():
    """Healthcheck de los compose (charter RF-03)."""
    return {"status": "ok", "modelo": v2.current_model_info()}
