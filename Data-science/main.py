"""
MDVA — Monitoreo de Variables Ambientales
FastAPI service for rain prediction models
Sprint 2 · KR2: Predicción pública de referencia
"""

import numpy as np
import joblib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from pathlib import Path
import math

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MDVA Predicción de Lluvia",
    description="Servicio de predicción binaria de lluvia para el Valle de Aburrá.",
    version="1.0.0",
)

# ── Model loading ──────────────────────────────────────────────────────────────
MODELS_DIR = Path(__file__).parent / "models"

def load_models():
    models = {}
    paths = {
        "regresion_logistica": MODELS_DIR / "regresion_logistica.pkl",
        "random_forest":       MODELS_DIR / "random_forest.pkl",
    }
    for name, path in paths.items():
        if not path.exists():
            raise RuntimeError(f"Modelo no encontrado: {path}")
        models[name] = joblib.load(path)
    return models

try:
    MODELS = load_models()
except RuntimeError as e:
    raise RuntimeError(str(e))


# ── Schemas ────────────────────────────────────────────────────────────────────
class ModeloNombre(str, Enum):
    regresion_logistica = "regresion_logistica"
    random_forest       = "random_forest"


class EntradaPrediccion(BaseModel):
    temperatura_c:          float = Field(..., example=18.5,  description="Temperatura en °C")
    humedad_relativa_pct:   float = Field(..., example=82.0,  description="Humedad relativa (%)")
    cobertura_nubosa_pct:   float = Field(..., example=75.0,  description="Cobertura nubosa (%)")
    velocidad_viento_ms:    float = Field(..., example=2.3,   description="Velocidad del viento (m/s)")
    hora:                   int   = Field(..., ge=0, le=23,    example=14,   description="Hora del día (0–23)")
    mes:                    int   = Field(..., ge=1, le=12,    example=4,    description="Mes del año (1–12)")


class ResultadoPrediccion(BaseModel):
    modelo:           str
    llueve:           bool
    probabilidad_lluvia: float = Field(..., description="Probabilidad de lluvia (0.0–1.0)")
    etiqueta:         str   = Field(..., description="'llueve' o 'no llueve'")


# ── Feature engineering ────────────────────────────────────────────────────────
def preparar_features(entrada: EntradaPrediccion) -> np.ndarray:
    """Replica exacta del preprocesamiento del notebook."""
    hora_sin = math.sin(2 * math.pi * entrada.hora / 24)
    hora_cos = math.cos(2 * math.pi * entrada.hora / 24)
    mes_sin  = math.sin(2 * math.pi * entrada.mes  / 12)
    mes_cos  = math.cos(2 * math.pi * entrada.mes  / 12)

    return np.array([[
        entrada.temperatura_c,
        entrada.humedad_relativa_pct,
        entrada.cobertura_nubosa_pct,
        entrada.velocidad_viento_ms,
        hora_sin, hora_cos,
        mes_sin,  mes_cos,
    ]])


# ── Helpers ────────────────────────────────────────────────────────────────────
def predecir(nombre_modelo: str, entrada: EntradaPrediccion) -> ResultadoPrediccion:
    modelo = MODELS[nombre_modelo]
    X = preparar_features(entrada)

    clase = int(modelo.predict(X)[0])
    proba = float(modelo.predict_proba(X)[0][1])   # P(llueve=1)

    return ResultadoPrediccion(
        modelo=nombre_modelo,
        llueve=bool(clase),
        probabilidad_lluvia=round(proba, 4),
        etiqueta="llueve" if clase else "no llueve",
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────
@app.get("/", tags=["Info"])
def raiz():
    return {"servicio": "MDVA Predicción de Lluvia", "version": "1.0.0", "modelos": list(MODELS.keys())}


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok", "modelos_cargados": list(MODELS.keys())}


@app.post(
    "/predecir/ambos",
    response_model=list[ResultadoPrediccion],
    tags=["Predicción"],
    summary="Predicción con ambos modelos en paralelo",
)
def predecir_ambos(entrada: EntradaPrediccion):
    """Devuelve las predicciones de los dos modelos en una sola llamada."""
    resultados = []
    for nombre in MODELS:
        try:
            resultados.append(predecir(nombre, entrada))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error en {nombre}: {e}")
    return resultados


@app.post(
    "/predecir/{modelo}",
    response_model=ResultadoPrediccion,
    tags=["Predicción"],
    summary="Predicción con un modelo específico",
)
def predecir_con_modelo(modelo: ModeloNombre, entrada: EntradaPrediccion):
    """
    Predice si lloverá dado un conjunto de variables meteorológicas.

    - **regresion_logistica** — más rápido, interpretable
    - **random_forest** — mayor ROC-AUC (0.82 vs 0.78 en prototipo)
    """
    try:
        return predecir(modelo.value, entrada)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))