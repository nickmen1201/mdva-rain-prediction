from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from presentation.api import router

app = FastAPI(
    title="MDVA Enrutamiento Ambiental",
    description=(
        "Sistema de Enrutamiento Inteligente para el Valle de Aburrá.\n\n"
        "Integra variables ambientales (SIATA + MDVA ML + Open-Meteo) "
        "con grafos viales OSMnx/NetworkX para calcular rutas óptimas "
        "que consideran lluvia, topografía y tráfico.\n\n"
        "**Endpoints principales:**\n"
        "- `POST /api/v1/route` — Ruta simple con opciones (fastest/shortest/dryest)\n"
        "- `POST /api/v1/route/multi` — Ruta multi-parada\n"
        "- `POST /api/v1/route/spring` — Compatible con Backend Spring Boot (reemplaza Google Directions)\n"
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "MDVA Enrutamiento Ambiental - Sistema integrado con variables ambientales.",
        "docs": "/docs",
        "endpoints": [
            "POST /api/v1/route — Ruta simple",
            "POST /api/v1/route/multi — Ruta multi-parada",
            "POST /api/v1/route/spring — Compatible Spring Boot",
        ],
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "enrutamiento-ambiental"}
