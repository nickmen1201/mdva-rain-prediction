import os
import requests
from domain.rain_model import RainModel


class WeatherService:
    """
    Servicio de clima integrado con MDVA.
    
    Combina dos fuentes de datos:
      1. El modelo de lluvia local (SIATA/RandomForest) para intensidad y penalización topográfica
      2. El microservicio MDVA de predicción ML (regresión logística + random forest)
         para probabilidad binaria de lluvia basada en variables ambientales reales
    
    El resultado final enriquece las rutas con TODOS los datos ambientales disponibles.
    """
    def __init__(self, rain_model: RainModel, mdva_ml_url: str = None, api_key: str = None):
        self.rain_model = rain_model
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        # URL del microservicio MDVA de predicción ML (Data-science/main.py)
        self.mdva_ml_url = mdva_ml_url or os.environ.get("MDVA_ML_URL", "http://ml-service:8081")
        self._mdva_cache = {}
        self._mdva_cache_time = 0

    def get_weather_stats(self, lat: float, lon: float) -> dict:
        """
        Retorna estadísticas detalladas de clima para un punto, incluyendo topografía.
        Enriquecido con predicción MDVA.
        """
        # 1. Obtener datos del modelo local (SIATA)
        stats = self.rain_model.get_current_probability_stats(lat, lon)
        
        intensity = stats["intensity"]
        probability = stats["probability"]
        elevation = stats["elevation"]
        
        # Factor de penalización (1.0 a 2.0)
        # Se agrava si la elevación es alta (las nubes chocan con las montañas)
        elevation_factor = 1.0 + (max(0, elevation - 1500) / 1000.0) * 0.2
        penalty = (1.0 + min(intensity / 5.0, 1.0)) * elevation_factor
        
        # 2. Obtener predicción MDVA (variables ambientales reales)
        mdva_prediction = self._get_mdva_prediction(lat, lon)
        
        # 3. Combinar: usar el máximo entre la predicción local y la de MDVA
        if mdva_prediction:
            mdva_prob = mdva_prediction.get("probabilidad_rf", 0.0)
            # Si MDVA dice que llueve con alta probabilidad, ajustar penalty
            if mdva_prob > 0.5:
                mdva_penalty_boost = 1.0 + (mdva_prob - 0.5) * 0.6  # hasta 0.3 extra
                penalty = max(penalty, mdva_penalty_boost * elevation_factor)
            # Usar la probabilidad más alta entre ambos modelos
            probability = max(probability, mdva_prob * 100.0)
        
        return {
            "intensity": intensity,
            "probability": probability,
            "penalty": penalty,
            "elevation": elevation,
            # Datos MDVA completos
            "mdva": mdva_prediction or {},
        }

    def get_rain_factor(self, lat: float, lon: float) -> float:
        stats = self.get_weather_stats(lat, lon)
        return stats["penalty"]

    def _get_mdva_prediction(self, lat: float, lon: float) -> dict:
        """
        Obtiene la predicción de lluvia del microservicio MDVA (Data-science/main.py).
        Primero obtiene variables climáticas de Open-Meteo, luego las envía al ML.
        """
        import time
        
        # Cache de 5 minutos
        cache_key = f"{lat:.2f},{lon:.2f}"
        if cache_key in self._mdva_cache and time.time() - self._mdva_cache_time < 300:
            return self._mdva_cache[cache_key]
        
        try:
            # Paso 1: Obtener variables climáticas actuales de Open-Meteo (gratis, sin API key)
            weather_data = self._get_open_meteo_data(lat, lon)
            if not weather_data:
                return None
            
            # Paso 2: Enviar al microservicio MDVA para predicción ML
            from datetime import datetime
            now = datetime.now()
            
            payload = {
                "temperatura_c": weather_data["temperature"],
                "humedad_relativa_pct": weather_data["humidity"],
                "cobertura_nubosa_pct": weather_data["cloud_cover"],
                "velocidad_viento_ms": weather_data["wind_speed"],
                "hora": now.hour,
                "mes": now.month,
            }
            
            response = requests.post(
                f"{self.mdva_ml_url}/predecir/ambos",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                predictions = response.json()
                
                # Consolidar resultado
                prob_rf = 0.0
                prob_rl = 0.0
                any_rain = False
                
                for pred in predictions:
                    modelo = pred.get("modelo", "")
                    prob = pred.get("probabilidad_lluvia", 0.0)
                    llueve = pred.get("llueve", False)
                    any_rain = any_rain or llueve
                    
                    if modelo == "random_forest":
                        prob_rf = prob
                    elif modelo == "regresion_logistica":
                        prob_rl = prob
                
                result = {
                    "llueve": any_rain,
                    "probabilidad_rf": prob_rf,
                    "probabilidad_rl": prob_rl,
                    "temperatura_c": weather_data["temperature"],
                    "humedad_pct": weather_data["humidity"],
                    "cobertura_nubosa_pct": weather_data["cloud_cover"],
                    "velocidad_viento_ms": weather_data["wind_speed"],
                }
                
                self._mdva_cache[cache_key] = result
                self._mdva_cache_time = time.time()
                return result
                
        except Exception as e:
            print(f"[MDVA Bridge] Error obteniendo predicción MDVA: {e}")
        
        return None

    def _get_open_meteo_data(self, lat: float, lon: float) -> dict:
        """
        Obtiene variables climáticas actuales de Open-Meteo (API gratuita, sin key).
        Esto es lo mismo que hace WeatherMLServiceImpl.java del Backend.
        """
        try:
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}"
                f"&current=temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m"
                f"&timezone=America/Bogota"
            )
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get("current", {})
                return {
                    "temperature": current.get("temperature_2m", 20.0),
                    "humidity": current.get("relative_humidity_2m", 70.0),
                    "cloud_cover": current.get("cloud_cover", 50.0),
                    "wind_speed": current.get("wind_speed_10m", 2.0) / 3.6,  # km/h → m/s
                }
        except Exception as e:
            print(f"[Open-Meteo] Error: {e}")
        
        # Fallback con valores promedio de Medellín
        return {
            "temperature": 22.0,
            "humidity": 75.0,
            "cloud_cover": 60.0,
            "wind_speed": 1.5,
        }
