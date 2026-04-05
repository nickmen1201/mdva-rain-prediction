package ti.mdva.service;

import ti.mdva.model.dto.RainPredictionDTO;

/**
 * Puerto para la integración clima → modelo ML.
 * Implementa el flujo del TODO del PowerShell en ViajeUseCase:
 *   1. Obtiene variables meteorológicas de Open-Meteo para lat/lng dadas
 *   2. Las envía al microservicio FastAPI (/predecir/ambos)
 *   3. Retorna el resultado consolidado
 */
public interface WeatherMLService {

    /**
     * Obtiene la predicción de lluvia para una ubicación y momento actuales.
     *
     * @param lat latitud del punto de origen del viaje
     * @param lng longitud del punto de origen del viaje
     * @return predicción con probabilidad de lluvia y variables climáticas
     */
    RainPredictionDTO predictRainForLocation(double lat, double lng);
}
