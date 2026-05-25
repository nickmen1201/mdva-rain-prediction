"""
Entrena el modelo de intensidad de lluvia (regressor) para el routing service.

Usa todos los 185 CSVs de SIATA pluviometria como fuente de datos real.
Guarda en ../cache/rain_model.joblib (ruta que carga el routing service).
"""
import pandas as pd
import glob
import os
import sys
from pathlib import Path
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from joblib import dump
import numpy as np

SCRIPT_DIR = Path(__file__).parent

# Ruta a los CSVs de SIATA (relativa al script)
DATA_PATH = SCRIPT_DIR / ".." / ".." / ".." / ".." / "pluviometrica" / "*.csv"
# Ruta de salida del modelo
MODEL_DIR  = SCRIPT_DIR / "cache"
MODEL_PATH = MODEL_DIR / "rain_model.joblib"

MAX_ROWS_PER_STATION = 50_000


def extract_station_id(filepath: str) -> int:
    """Extrae el station_id del nombre de archivo: Estacion_pluviometrica_<ID>_..."""
    basename = os.path.basename(filepath)
    parts = basename.split("_")
    try:
        return int(parts[2])
    except (IndexError, ValueError):
        # Fallback: usa hash del nombre para ser determinista
        return abs(hash(basename)) % 10000


def load_station(filepath: str) -> pd.DataFrame | None:
    try:
        df = pd.read_csv(
            filepath,
            usecols=["fecha_hora", "p1", "calidad"],
            parse_dates=["fecha_hora"],
        )
        # Filtrar calidad OK y lecturas válidas
        df = df[(df["calidad"] == 1) & (df["p1"] >= 0)].copy()
        if len(df) == 0:
            return None

        # Limitar datos por estación para balance
        df = df.sort_values("fecha_hora").tail(MAX_ROWS_PER_STATION)

        station_id = extract_station_id(filepath)

        # Ingeniería de características (ventanas de 60 y 180 registros ≈ 1h y 3h)
        df = df.sort_values("fecha_hora").reset_index(drop=True)
        df["p1_rolling_mean_1h"] = df["p1"].rolling(window=60, min_periods=1).mean()
        df["p1_rolling_max_3h"]  = df["p1"].rolling(window=180, min_periods=1).max()
        df["p1_rolling_std_1h"]  = df["p1"].rolling(window=60, min_periods=1).std().fillna(0)

        df["hour"]        = df["fecha_hora"].dt.hour
        df["month"]       = df["fecha_hora"].dt.month
        df["day_of_week"] = df["fecha_hora"].dt.dayofweek
        df["station_id"]  = station_id

        # Altitud aproximada por station_id (proxy topográfico)
        df["elevation_approx"] = 1500 + (station_id % 50) * 20

        return df

    except Exception as e:
        print(f"  [WARN] Error procesando {filepath}: {e}", file=sys.stderr)
        return None


def train_model():
    files = sorted(glob.glob(str(DATA_PATH)))
    if not files:
        # Fallback: buscar con ruta absoluta del proyecto si la relativa falla
        alt_path = Path("C:/Users/Luis Seoanes/Desktop/Ciencia de datos/Quinto semestre/Proyecto en tic/pluviometrica/*.csv")
        files = sorted(glob.glob(str(alt_path)))

    print(f"Encontrados {len(files)} archivos de estaciones. Procesando TODOS con max {MAX_ROWS_PER_STATION} filas c/u...")

    FEATURES = [
        "hour", "month", "day_of_week", "station_id",
        "p1_rolling_mean_1h", "p1_rolling_max_3h", "p1_rolling_std_1h",
        "elevation_approx",
    ]
    TARGET = "p1"

    all_chunks = []
    ok_count = 0

    for i, fpath in enumerate(files):
        df = load_station(fpath)
        if df is not None:
            all_chunks.append(df[FEATURES + [TARGET]])
            ok_count += 1
        if (i + 1) % 20 == 0:
            print(f"  Procesadas {i+1}/{len(files)} estaciones ({ok_count} OK)...")

    if not all_chunks:
        print("ERROR: No se cargaron datos.", file=sys.stderr)
        sys.exit(1)

    full_df = pd.concat(all_chunks, ignore_index=True)
    print(f"\nTotal registros: {len(full_df):,} de {ok_count} estaciones")
    print(f"Distribución p1: media={full_df[TARGET].mean():.3f}, max={full_df[TARGET].max():.1f}")

    X = full_df[FEATURES].values
    y = full_df[TARGET].values

    print(f"\nEntrenando RandomForestRegressor(n_estimators=50, max_depth=10)...")
    model = RandomForestRegressor(
        n_estimators=50,
        max_depth=10,
        n_jobs=-1,
        min_samples_leaf=5,
        random_state=42,
    )
    model.fit(X, y)

    # Evaluación sobre muestra de entrenamiento (proxy de RMSE)
    sample_idx = np.random.choice(len(X), size=min(50_000, len(X)), replace=False)
    y_pred = model.predict(X[sample_idx])
    rmse = np.sqrt(mean_squared_error(y[sample_idx], y_pred))
    r2   = model.score(X[sample_idx], y[sample_idx])
    print(f"RMSE (train sample): {rmse:.4f} mm/min")
    print(f"R²   (train sample): {r2:.4f}")

    print("\nImportancia de features:")
    for feat, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {feat:<30} {imp:.4f}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dump(model, MODEL_PATH)
    size_mb = MODEL_PATH.stat().st_size / 1e6
    print(f"\nModelo guardado en: {MODEL_PATH} ({size_mb:.1f} MB)")
    print("Listo.")


if __name__ == "__main__":
    train_model()
