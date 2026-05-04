import pandas as pd
import glob
import os
from sklearn.ensemble import RandomForestRegressor
from joblib import dump
import numpy as np

def train_model():
    data_path = "../../../pluviometrica/*.csv"
    files = glob.glob(data_path)
    
    all_data = []
    
    print(f"Encontrados {len(files)} archivos de estaciones. Procesando muestra con estadísticas avanzadas...")
    
    for f in files[:30]: # Aumentamos la muestra a 30 estaciones
        try:
            df = pd.read_csv(f, usecols=['fecha_hora', 'p1'], parse_dates=['fecha_hora'])
            df = df.tail(20000) # Más datos para promedios móviles
            
            # --- Ingeniería de Características Estadísticas ---
            df = df.sort_values('fecha_hora')
            df['p1_rolling_mean_1h'] = df['p1'].rolling(window=60, min_periods=1).mean()
            df['p1_rolling_max_3h'] = df['p1'].rolling(window=180, min_periods=1).max()
            df['p1_rolling_std_1h'] = df['p1'].rolling(window=60, min_periods=1).std().fillna(0)
            
            # Características temporales
            df['hour'] = df['fecha_hora'].dt.hour
            df['month'] = df['fecha_hora'].dt.month
            df['day_of_week'] = df['fecha_hora'].dt.dayofweek
            
            station_id = int(os.path.basename(f).split('_')[2])
            df['station_id'] = station_id
            
            # Altitud ficticia basada en el station_id para el modelo topográfico (si no tenemos la real)
            # Generalmente IDs más altos en SIATA son estaciones más nuevas o periféricas (más altas)
            df['elevation_approx'] = 1500 + (station_id % 50) * 20 
            
            features = ['hour', 'month', 'day_of_week', 'station_id', 
                        'p1_rolling_mean_1h', 'p1_rolling_max_3h', 'p1_rolling_std_1h', 'elevation_approx']
            
            all_data.append(df[features + ['p1']])
        except Exception as e:
            print(f"Error procesando {f}: {e}")
            
    if not all_data:
        print("No se pudo cargar ningún dato.")
        return
        
    full_df = pd.concat(all_data)
    X = full_df.drop('p1', axis=1)
    y = full_df['p1']
    
    print(f"Entrenando modelo avanzado con {len(full_df)} registros...")
    # Usamos más árboles para mejor precisión
    model = RandomForestRegressor(n_estimators=100, max_depth=12, n_jobs=-1)
    model.fit(X, y)
    
    model_dir = "../cache"
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
        
    dump(model, os.path.join(model_dir, "rain_model.joblib"))
    print("Modelo avanzado guardado en cache/rain_model.joblib")

if __name__ == "__main__":
    train_model()
