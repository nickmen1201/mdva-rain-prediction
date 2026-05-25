"""
Entrena random_forest.pkl y regresion_logistica.pkl usando SIATA como ground truth.

Estrategia:
  - 185 CSVs de pluviometría SIATA → etiquetas reales de lluvia (no Open-Meteo weather_code)
  - Open-Meteo Archive API → features meteorológicas (temperatura, humedad, viento, etc.)
  - Join en hora → features + etiqueta real
  - precip_lag_1h_mm viene del promedio SIATA real (no estimado)

Features de inferencia (deben coincidir con EntradaPrediccion en main.py):
  temperatura_c, humedad_relativa_pct, cobertura_nubosa_pct, velocidad_viento_ms,
  hora_sin, hora_cos, mes_sin, mes_cos, precip_lag_1h_mm
"""
import time
import math
import glob
import sys
import requests
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

MODELS_DIR  = Path(__file__).parent / "models"
PLUVIO_DIR  = Path(__file__).parent / ".." / ".." / ".." / "pluviometrica"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

LLUVIA_UMBRAL_MM = 0.1   # mm/hora → llueve=1
# Rango con mejor cobertura SIATA
DATE_START = "2018-01-01"
DATE_END   = "2025-12-31"

# ── Paso 1: Agregar pluviometría SIATA a promedios horarios del Valle ─────────

def cargar_siata_hourly() -> pd.DataFrame:
    """
    Lee todos los CSVs de SIATA, agrega a totales horarios por estación
    y luego promedia entre estaciones para obtener precipitación del Valle.
    """
    pattern = str(PLUVIO_DIR / "*.csv")
    files   = sorted(glob.glob(pattern))

    if not files:
        # Fallback: ruta absoluta en caso de que el CWD sea diferente
        abs_path = Path("C:/Users/Luis Seoanes/Desktop/Ciencia de datos/Quinto semestre/Proyecto en tic/pluviometrica/*.csv")
        files = sorted(glob.glob(str(abs_path)))

    if not files:
        print("ERROR: No se encontraron CSVs de pluviometría. Verifica PLUVIO_DIR.", file=sys.stderr)
        sys.exit(1)

    print(f"Cargando {len(files)} estaciones SIATA...")

    station_dfs = []
    ok = 0
    for i, fpath in enumerate(files):
        try:
            df = pd.read_csv(
                fpath,
                usecols=["codigo", "fecha_hora", "p1", "calidad"],
                parse_dates=["fecha_hora"],
            )
            # Filtrar calidad OK y valores válidos
            df = df[(df["calidad"] == 1) & (df["p1"] >= 0)].copy()
            if len(df) < 100:
                continue

            # Truncar a la hora
            df["hora"] = df["fecha_hora"].dt.floor("h")

            # Sumar p1 por hora para esta estación
            hourly = df.groupby("hora")["p1"].sum().reset_index()
            hourly.columns = ["hora", "precip_mm_h"]
            hourly["station"] = df["codigo"].iloc[0]
            station_dfs.append(hourly)
            ok += 1
        except Exception as e:
            pass  # Ignorar estaciones con problemas

        if (i + 1) % 30 == 0:
            print(f"  {i+1}/{len(files)} procesadas ({ok} OK)...")

    print(f"  Estaciones cargadas con éxito: {ok}")

    all_st = pd.concat(station_dfs, ignore_index=True)

    # Filtrar rango de fechas con mejor cobertura
    all_st = all_st[(all_st["hora"] >= DATE_START) & (all_st["hora"] <= DATE_END)]

    # Promedio del Valle por hora (media entre estaciones activas)
    valle_hourly = (
        all_st.groupby("hora")["precip_mm_h"]
        .mean()
        .reset_index()
        .rename(columns={"precip_mm_h": "precip_valle_mm_h"})
    )
    valle_hourly = valle_hourly.sort_values("hora").reset_index(drop=True)

    # Etiqueta: llueve si precip >= 0.1 mm/h
    valle_hourly["llueve"] = (valle_hourly["precip_valle_mm_h"] >= LLUVIA_UMBRAL_MM).astype(int)

    # Lag de 1 hora (precip hora anterior)
    valle_hourly["precip_lag_1h_mm"] = valle_hourly["precip_valle_mm_h"].shift(1).fillna(0.0)

    print(f"Horas con datos SIATA: {len(valle_hourly):,}")
    print(f"Llueve en {valle_hourly['llueve'].mean()*100:.1f}% de las horas")
    return valle_hourly


# ── Paso 2: Descargar features de Open-Meteo (solo La Candelaria) ─────────────

def descargar_openmeteo(lat: float = 6.2518, lon: float = -75.5636) -> pd.DataFrame:
    """
    Descarga features meteorológicas del archivo Open-Meteo para La Candelaria.
    Solo descarga un punto para ser más rápido y confiable.
    """
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": DATE_START,
        "end_date": DATE_END,
        "hourly": ",".join([
            "temperature_2m",
            "relative_humidity_2m",
            "cloud_cover",
            "wind_speed_10m",
        ]),
        "timezone": "America/Bogota",
    }
    print(f"Descargando Open-Meteo ({DATE_START} → {DATE_END}) para La Candelaria...")
    for intento in range(3):
        resp = requests.get(url, params=params, timeout=120)
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
    df["hora"] = pd.to_datetime(df["time"]).dt.tz_localize(None)
    df = df.rename(columns={
        "temperature_2m": "temperatura_c",
        "relative_humidity_2m": "humedad_relativa_pct",
        "cloud_cover": "cobertura_nubosa_pct",
        "wind_speed_10m": "velocidad_viento_ms",
    })
    df = df.drop(columns=["time"])
    print(f"Open-Meteo: {len(df):,} registros horarios")
    return df


# ── Paso 3: Unir y entrenar ───────────────────────────────────────────────────

def main():
    # Cargar SIATA
    siata = cargar_siata_hourly()

    # Descargar Open-Meteo
    weather = descargar_openmeteo()

    # Join en hora
    df = pd.merge(siata, weather, on="hora", how="inner")
    print(f"\nRegistros tras join (SIATA ∩ Open-Meteo): {len(df):,}")
    if len(df) < 1000:
        print("ERROR: muy pocos registros tras el join. Revisar fechas.", file=sys.stderr)
        sys.exit(1)

    # Feature engineering temporal (cyclic encoding)
    df["hora_sin"] = np.sin(2 * np.pi * df["hora"].dt.hour / 24)
    df["hora_cos"] = np.cos(2 * np.pi * df["hora"].dt.hour / 24)
    df["mes_sin"]  = np.sin(2 * np.pi * df["hora"].dt.month / 12)
    df["mes_cos"]  = np.cos(2 * np.pi * df["hora"].dt.month / 12)

    df = df.dropna()
    print(f"Registros tras dropna: {len(df):,} | Llueve: {df['llueve'].mean()*100:.1f}%")

    FEATURES = [
        "temperatura_c",
        "humedad_relativa_pct",
        "cobertura_nubosa_pct",
        "velocidad_viento_ms",
        "hora_sin",
        "hora_cos",
        "mes_sin",
        "mes_cos",
        "precip_lag_1h_mm",
    ]

    X = df[FEATURES].values
    y = df["llueve"].values

    # ── Entrenar RF ────────────────────────────────────────────────────────────
    print("\nEntrenando Random Forest (100 árboles, SIATA ground truth)...")
    rf = RandomForestClassifier(
        n_estimators=100,
        max_depth=14,
        min_samples_leaf=15,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X, y)

    # ── Entrenar RL ────────────────────────────────────────────────────────────
    print("Entrenando Regresión Logística...")
    rl = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    rl.fit(X, y)

    # ── Cross-validation ───────────────────────────────────────────────────────
    print("Evaluando RF con cross-validation (3 folds)...")
    auc_scores = cross_val_score(rf, X, y, cv=3, scoring="roc_auc", n_jobs=-1)
    print(f"RF  AUC: {auc_scores.mean():.4f} ± {auc_scores.std():.4f}")

    auc_rl = cross_val_score(rl, X, y, cv=3, scoring="roc_auc", n_jobs=-1)
    print(f"RL  AUC: {auc_rl.mean():.4f} ± {auc_rl.std():.4f}")

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


if __name__ == "__main__":
    main()
