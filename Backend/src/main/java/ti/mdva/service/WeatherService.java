package ti.mdva.service;

import ti.mdva.dto.WeatherRequestDTO;
import ti.mdva.dto.WeatherResponseDTO;

/**
 * Service interface for weather operations using Open-Meteo API.
 */
public interface WeatherService {

    /**
     * Fetches current weather data for given coordinates.
     *
     * @param request the weather request with coordinates
     * @return current weather data
     */
    WeatherResponseDTO getCurrentWeather(WeatherRequestDTO request);
}
