package ti.mdva.service;

import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.service.weather.HourlyInputs;

import java.util.List;

/**
 * Puerto para la integración clima → modelo ML (specs/007-backend-weather-openmeteo).
 *
 * Todas las operaciones obtienen las 9 variables del pronóstico de Open-Meteo (la misma
 * fuente del entrenamiento) y predicen con el ML API v2.
 */
public interface WeatherMLService {

    /**
     * Predicción para la hora en curso en lat/lng.
     */
    RainPredictionDTO predictRainForLocation(double lat, double lng);

    /**
     * Entradas del modelo para la hora en curso en lat/lng (las usa el monitoreo de trayecto).
     */
    HourlyInputs currentInputs(double lat, double lng);

    /**
     * Predicción horaria para las próximas N horas en lat/lng.
     *
     * @param lat latitud
     * @param lng longitud
     * @param horas cantidad de horas a futuro (1-24, recomendado 6-12)
     * @return lista ordenada de predicciones horarias
     */
    List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas);

    /**
     * Prediccion de lluvia para una grilla de puntos usada por el heatmap.
     */
    WeatherGridResponseDTO predictGridForArea(List<WeatherGridPointDTO> puntos);
}
