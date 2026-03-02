package ti.mdva.service;

import ti.mdva.dto.WeatherResponseDTO;

/**
 * Service interface for weather data operations.
 *
 * @author MDVA Team
 * @version 1.0
 */
public interface WeatherService {

    /**
     * Retrieves current weather conditions and forecast for a location.
     *
     * @param latitude  latitude coordinate
     * @param longitude longitude coordinate
     * @return weather data including current conditions and 24-hour forecast
     */
    WeatherResponseDTO getCurrentWeather(Double latitude, Double longitude);
}
