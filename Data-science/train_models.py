"""
Entrena random_forest.pkl y regresion_logistica.pkl.

Mejoras sobre v1:
  - 8 puntos del Valle de Aburrá (no solo La Candelaria)
  - weather_code → precipitacion_prob_pct (proxy de "probabilidad tipo Google")
  - precip_lag_1h: mm caídos en la hora anterior (predictor más fuerte de lluvia inminente)
  - n_estimators=100 con max_depth=14 (mejor AUC que v1 gracias a más datos)

Features de inferencia (deben coincidir con EntradaPrediccion en main.py):
  temperatura_c, humedad_relativa_pct, cobertura_nubosa_pct, velocidad_viento_ms,
  hora_sin, hora_cos, mes_sin, mes_cos,
  precipitacion_prob_pct, precip_lag_1h_mm
"""
import time
import math
import requests
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

MODELS_DIR = Path(__file__).parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

LLUVIA_UMBRAL_MM = 0.1

PUNTOS = [
    ("Barbosa",    6.4370, -75.3317),
    ("Bello",      6.3367, -75.5567),
    ("Robledo",    6.2833, -75.6000),
    ("Candelaria", 6.2518, -75.5636),
    ("Poblado",    6.2100, -75.5600),
    ("Envigado",   6.1719, -75.5906),
    ("Itagui",     6.1847, -75.6144),
    ("Caldas",     6.0942, -75.6367),
]

# WMO weather_code → probabilidad de lluvia estimada (0–100)
# Docs: https://open-meteo.com/en/docs#weathervariables
WCODE_TO_PROB = {
    **{c: 0   for c in range(0, 4)},    # despejado / nubes parciales
    **{c: 5   for c in range(4, 13)},   # niebla ligera
    **{c: 15  for c in range(13, 20)},  # fenómenos leves
    **{c: 25  for c in range(20, 30)},  # precipitación ligera pasada
    **{c: 20  for c in range(30, 40)},  # tormenta de polvo
    **{c: 30  for c in range(40, 50)},  # niebla
    **{c: 60  for c in range(50, 60)},  # llovizna
    **{c: 70  for c in range(60, 70)},  # lluvia
    **{c: 65  for c in range(70, 78)},  # nieve (no aplica en Medellín)
    **{c: 75  for c in range(78, 80)},  # granizo de nieve
    **{c: 80  for c in range(80, 83)},  # chubascos ligeros
    **{c: 90  for c in range(83, 87)},  # chubascos fuertes
    **{c: 85  for c in range(87, 92)},  # granizo
    **{c: 92  for c in range(92, 96)},  # tormenta ligera
    **{c: 98  for c in range(96, 100)}, # tormenta fuerte
}


def weather_code_to_prob(code):
    return WCODE_TO_PROB.get(int(code) if not math.isnan(code) else 0, 50)


def descargar_punto(nombre, lat, lon):
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": "2016-01-01",
        "end_date": "2025-04-30",
        "hourly": ",".join([
            "precipitation",
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "wind_speed_10m",
            "weather_code",
        ]),
        "timezone": "America/Bogota",
    }
    for intento in range(3):
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code == 200:
            break
        if resp.status_code == 429:
            espera = 60 * (intento + 1)
            print(f"  Rate limit — esperando {espera}s...")
            time.sleep(espera)
        else:
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
        "weather_code": "weather_code",
    })
    df["punto"] = nombre
    return df


print("Descargando datos de 8 puntos del Valle de Aburrá (2016–2025)...")
dfs = []
for i, (nombre, lat, lon) in enumerate(PUNTOS):
    print(f"  [{i+1}/8] {nombre}...")
    df = descargar_punto(nombre, lat, lon)
    dfs.append(df)
    if i < len(PUNTOS) - 1:
        time.sleep(12)   # respeta el rate limit de Open-Meteo

df_all = pd.concat(dfs, ignore_index=True)
print(f"Total: {len(df_all):,} registros de {df_all['punto'].nunique()} puntos")

# ── Feature engineering ────────────────────────────────────────────────────
df_all = df_all.sort_values(["punto", "time"]).reset_index(drop=True)

# Precipitación real de la hora anterior (dentro del mismo punto)
df_all["precip_lag_1h_mm"] = (
    df_all.groupby("punto")["precipitacion_mm"]
    .shift(1)
    .fillna(0.0)
)

# weather_code → proxy de probabilidad de lluvia (similar a lo que Google Weather reporta)
df_all["precipitacion_prob_pct"] = df_all["weather_code"].apply(weather_code_to_prob)

# Cyclic encoding de tiempo
df_all["hora"] = df_all["time"].dt.hour
df_all["mes"]  = df_all["time"].dt.month
df_all["hora_sin"] = np.sin(2 * np.pi * df_all["hora"] / 24)
df_all["hora_cos"] = np.cos(2 * np.pi * df_all["hora"] / 24)
df_all["mes_sin"]  = np.sin(2 * np.pi * df_all["mes"]  / 12)
df_all["mes_cos"]  = np.cos(2 * np.pi * df_all["mes"]  / 12)

# Target
df_all["llueve"] = (df_all["precipitacion_mm"] >= LLUVIA_UMBRAL_MM).astype(int)
df_all = df_all.dropna()

print(f"Registros tras limpieza: {len(df_all):,} | Lluvia: {df_all['llueve'].mean()*100:.1f}%")

FEATURES = [
    "temperatura_c",
    "humedad_relativa_pct",
    "cobertura_nubosa_pct",
    "velocidad_viento_ms",
    "hora_sin",
    "hora_cos",
    "mes_sin",
    "mes_cos",
    "precip_lag_1h_mm",   # precipitación hora anterior (sin data leakage)
    # precipitacion_prob_pct excluida: derivarla del weather_code causa leakage
    # ya que weather_code ≈ label. La prob. de Google se blendea en el backend.
]

X = df_all[FEATURES].values
y = df_all["llueve"].values

# ── Entrenamiento ──────────────────────────────────────────────────────────
print("Entrenando Random Forest (100 árboles)...")
rf = RandomForestClassifier(
    n_estimators=100,
    max_depth=14,
    min_samples_leaf=15,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)
rf.fit(X, y)

print("Entrenando Logistic Regression...")
rl = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
rl.fit(X, y)

# ── Evaluación rápida con CV ───────────────────────────────────────────────
print("Evaluando RF con cross-validation (3 folds)...")
auc_scores = cross_val_score(rf, X, y, cv=3, scoring="roc_auc", n_jobs=-1)
print(f"RF AUC: {auc_scores.mean():.4f} ± {auc_scores.std():.4f}")

# ── Importancia de features ────────────────────────────────────────────────
print("\nImportancia de features RF:")
for feat, imp in sorted(zip(FEATURES, rf.feature_importances_), key=lambda x: -x[1]):
    print(f"  {feat:<30} {imp:.4f}")

# ── Guardar ────────────────────────────────────────────────────────────────
rf_path = MODELS_DIR / "random_forest.pkl"
rl_path = MODELS_DIR / "regresion_logistica.pkl"
joblib.dump(rf, rf_path)
joblib.dump(rl, rl_path)
print(f"\nGuardado: {rf_path} ({rf_path.stat().st_size / 1e6:.1f} MB)")
print(f"Guardado: {rl_path}")
print("Listo.")
