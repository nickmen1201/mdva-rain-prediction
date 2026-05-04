import os
import joblib
import pandas as pd
from datetime import datetime


class RainModel:
    def __init__(self, model_path="../cache/rain_model.joblib"):
        self.model_path = model_path
        self.model = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                print(f"Modelo de lluvia cargado desde {self.model_path}")
            except Exception as e:
                print(f"Error cargando el modelo de lluvia: {e}")
        else:
            print(f"Advertencia: Modelo de lluvia no encontrado en {self.model_path}")

    def predict_rain_intensity(self, hour: int, month: int, day_of_week: int, station_id: int = 1, 
                               rolling_mean: float = 0.0, rolling_max: float = 0.0, 
                               rolling_std: float = 0.0, elevation: float = 1500.0) -> float:
        """
        Predice la intensidad de lluvia (p1) usando el modelo avanzado.
        """
        if self.model is None:
            return 0.0
            
        features = pd.DataFrame([[hour, month, day_of_week, station_id, 
                                 rolling_mean, rolling_max, rolling_std, elevation]], 
                               columns=['hour', 'month', 'day_of_week', 'station_id',
                                        'p1_rolling_mean_1h', 'p1_rolling_max_3h', 
                                        'p1_rolling_std_1h', 'elevation_approx'])
        
        try:
            prediction = self.model.predict(features)[0]
            return max(0.0, float(prediction))
        except Exception as e:
            print(f"Error en predicción: {e}")
            return 0.0

    def get_current_probability_stats(self, lat: float = 6.25, lon: float = -75.57) -> dict:
        """
        Obtiene estadísticas completas basadas en el momento actual y ubicación.
        """
        now = datetime.now()
        # Estimamos la elevación según la ubicación (simplificado: valle central vs laderas)
        # El centro de Medellín está a ~1495m. Las laderas suben hasta ~2500m.
        dist_from_river = abs(lon - (-75.57)) * 100000 # aprox metros
        est_elevation = 1500 + (dist_from_river / 10.0) # sube 10m por cada 100m de distancia al río
        
        # Para la demo, simulamos que hay algo de lluvia previa si es tarde
        simulated_mean = 0.2 if now.hour > 14 else 0.0
        
        intensity = self.predict_rain_intensity(
            now.hour, now.month, now.weekday(), 
            station_id=1, 
            rolling_mean=simulated_mean,
            rolling_max=simulated_mean * 2,
            rolling_std=simulated_mean * 0.5,
            elevation=est_elevation
        )
        
        return {
            "intensity": intensity,
            "elevation": est_elevation,
            "probability": min(intensity * 25.0, 100.0)
        }
