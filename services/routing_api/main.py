import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from presentation.api import router

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def allowed_origins() -> list[str]:
    """Orígenes de `CORS_ALLOWED_ORIGINS` (coma-separados). Vacío: ninguno (el Backend llama servidor a servidor)."""
    return [o.strip() for o in os.environ.get("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]


app = FastAPI(
    title="MDVA Enrutamiento Ambiental",
    description=(
        "Rutas sobre el grafo vial OSM del Valle de Aburrá con tiempos por tipo de vía y la probabilidad de "
        "lluvia del modelo evaluado (ML API v2).\n\n"
        "- `POST /api/v1/route` — opciones fastest / shortest / dryest\n"
        "- `POST /api/v1/route/multi` — ruta multi-parada\n"
        "- `POST /api/v1/route/spring` — formato del Backend\n"
        "- `POST /api/v1/route/metrics` — solo la señal de lluvia\n"
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(router)


@app.get("/")
def root():
    return {"message": "MDVA Enrutamiento Ambiental", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "enrutamiento-ambiental"}
