package ti.mdva.service;

import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;

import java.util.List;

import java.util.List;

/**
 * Puerto para la integración clima → modelo ML.
 *
 * Flujo principal (predictRainForLocation):
 *   1. Obtiene variables meteorológicas actuales (Google Weather)
 *   2. Las envía al microservicio FastAPI (/predecir/ambos)
 *   3. Retorna el resultado consolidado
 *
 * Flujo horario (getHourlyForecast):
 *   1. Obtiene variables meteorológicas hora-por-hora (Open-Meteo, gratis)
 *   2. Para cada hora futura, llama al ML con esas variables → probabilidad
 *   3. Retorna lista de predicciones horarias
 */
public interface WeatherMLService {

    /**
     * Predicción puntual ahora mismo en lat/lng.
     */
    RainPredictionDTO predictRainForLocation(double lat, double lng);

    /**
     * Predicción horaria para las próximas N horas en lat/lng.
     *
     * @param lat latitud
     * @param lng longitud
     * @param horas cantidad de horas a futuro (1-24, recomendado 6-12)
     * @return lista ordenada de predicciones horarias
     */
    List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas);
}
