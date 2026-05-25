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
        if path.exists():
            models[name] = joblib.load(path)
        else:
            print(f"[WARN] Modelo omitido (archivo no encontrado): {path}")
    if not models:
        raise RuntimeError(f"No se encontró ningún modelo en: {MODELS_DIR}")
    return models

MODELS = load_models()


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
    precip_lag_1h_mm:       float = Field(default=0.0, ge=0, example=0.0,
                                          description="Precipitación caída en la última hora (mm)")


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
        entrada.precip_lag_1h_mm,
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


# ── Sprint 5.2A: Monitoreo de Trayecto ─────────────────────────────────────────

class SnapshotCondiciones(BaseModel):
    probabilidad_rf_inicio: float
    temperatura_inicio: float
    timestamp_snapshot: str
    timestamp_dato_weather: str

class MonitoreoRequest(BaseModel):
    snapshot: SnapshotCondiciones
    condiciones_actuales: EntradaPrediccion

class MonitoreoResponse(BaseModel):
    probabilidad_rf_actual: float
    delta_probabilidad: float
    dato_con_latencia: bool
    minutos_latencia: int
    nivel_cambio: str

@app.post(
    "/monitorear/trayecto",
    response_model=MonitoreoResponse,
    tags=["Monitoreo"],
    summary="Evalúa el cambio de condiciones durante el trayecto",
)
def monitorear_trayecto(req: MonitoreoRequest):
    """
    Compara las condiciones iniciales con las actuales.
    Retorna el nivel de cambio y si hay latencia en los datos.
    """
    from datetime import datetime, timezone
    
    # 1. Calcular predicción actual usando RF (mayor AUC) o el primer modelo disponible
    target_model = "random_forest" if "random_forest" in MODELS else list(MODELS.keys())[0]
    res_actual = predecir(target_model, req.condiciones_actuales)
    prob_actual = res_actual.probabilidad_lluvia

    
    # 2. Calcular delta
    delta = prob_actual - req.snapshot.probabilidad_rf_inicio
    
    # 3. Calcular latencia: cuánto tiempo lleva el dato meteorológico inicial
    # respecto a la posición actual del trayecto. Si supera el umbral, la
    # confianza en la comparación baja y la regla del Sprint 5.2A "sube un nivel".
    try:
        ts_weather = datetime.fromisoformat(req.snapshot.timestamp_dato_weather.replace('Z', '+00:00'))
        ahora = datetime.now(timezone.utc)
        minutos_latencia = int((ahora - ts_weather).total_seconds() / 60)
        minutos_latencia = max(0, minutos_latencia)
    except Exception:
        minutos_latencia = 0

    con_latencia = minutos_latencia > 15
    
    # 4. Determinar nivel de cambio
    nivel_cambio = "ESTABLE"
    if delta >= 0.10 and delta <= 0.25:
        nivel_cambio = "MODERADO"
    elif delta > 0.25:
        nivel_cambio = "SIGNIFICATIVO"
        
    if con_latencia and nivel_cambio != "CRITICO":
        # Sube un nivel si hay latencia
        niveles = ["ESTABLE", "MODERADO", "SIGNIFICATIVO", "CRITICO"]
        idx = niveles.index(nivel_cambio)
        if idx < len(niveles) - 1:
            nivel_cambio = niveles[idx + 1]
            
    if prob_actual > 0.85:
        nivel_cambio = "CRITICO"
        
    return MonitoreoResponse(
        probabilidad_rf_actual=prob_actual,
        delta_probabilidad=delta,
        dato_con_latencia=con_latencia,
        minutos_latencia=minutos_latencia,
        nivel_cambio=nivel_cambio
    )