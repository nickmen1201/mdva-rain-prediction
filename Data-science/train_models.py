"""
Entrena y guarda random_forest.pkl (y regresion_logistica.pkl como backup).
Usa datos históricos de Open-Meteo para La Candelaria, Medellín.
Ejecutar con scikit-learn==1.4.2 para compatibilidad con el servicio de producción.
"""
import sys
import math
import requests
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

LAT, LON = 6.2518, -75.5636  # Centro (La Candelaria)
LLUVIA_UMBRAL_MM = 0.1

print("Descargando datos históricos de Open-Meteo (2018-2025)...")
url = "https://archive-api.open-meteo.com/v1/archive"
params = {
    "latitude": LAT,
    "longitude": LON,
    "start_date": "2018-01-01",
    "end_date": "2025-04-30",
    "hourly": "precipitation,temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m",
    "timezone": "America/Bogota",
}
resp = requests.get(url, params=params, timeout=60)
resp.raise_for_status()
data = resp.json()["hourly"]

df = pd.DataFrame(data)
df["time"] = pd.to_datetime(df["time"])
df = df.rename(columns={
    "precipitation": "precipitacion_mm",
    "temperature_2m": "temperatura_c",
    "relative_humidity_2m": "humedad_relativa_pct",
    "cloud_cover": "cobertura_nubosa_pct",
    "wind_speed_10m": "velocidad_viento_ms",
})
df["hora"] = df["time"].dt.hour
df["mes"] = df["time"].dt.month
df["llueve"] = (df["precipitacion_mm"] >= LLUVIA_UMBRAL_MM).astype(int)
df = df.dropna()

print(f"Registros: {len(df):,} | Lluvia: {df['llueve'].mean()*100:.1f}%")

df["hora_sin"] = np.sin(2 * np.pi * df["hora"] / 24)
df["hora_cos"] = np.cos(2 * np.pi * df["hora"] / 24)
df["mes_sin"]  = np.sin(2 * np.pi * df["mes"] / 12)
df["mes_cos"]  = np.cos(2 * np.pi * df["mes"] / 12)

FEATURES = [
    "temperatura_c", "humedad_relativa_pct", "cobertura_nubosa_pct",
    "velocidad_viento_ms", "hora_sin", "hora_cos", "mes_sin", "mes_cos",
]
X = df[FEATURES].values
y = df["llueve"].values

print("Entrenando Random Forest...")
rf = RandomForestClassifier(
    n_estimators=50,
    max_depth=12,
    min_samples_leaf=20,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)
rf.fit(X, y)

print("Entrenando Logistic Regression...")
rl = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
rl.fit(X, y)

rf_path = MODELS_DIR / "random_forest.pkl"
rl_path = MODELS_DIR / "regresion_logistica.pkl"
joblib.dump(rf, rf_path)
joblib.dump(rl, rl_path)
print(f"Guardado: {rf_path}")
print(f"Guardado: {rl_path}")
print("Listo.")
