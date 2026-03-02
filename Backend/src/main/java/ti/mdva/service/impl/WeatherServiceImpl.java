package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import ti.mdva.dto.WeatherRequestDTO;
import ti.mdva.dto.WeatherResponseDTO;
import ti.mdva.service.WeatherService;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Implementation of WeatherService using Open-Meteo API.
 */
@Service
public class WeatherServiceImpl implements WeatherService {

    private static final String OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";
    private static final Map<Integer, String> WEATHER_CODES = Map.ofEntries(
            Map.entry(0, "Clear sky"),
            Map.entry(1, "Mainly clear"),
            Map.entry(2, "Partly cloudy"),
            Map.entry(3, "Overcast"),
            Map.entry(45, "Fog"),
            Map.entry(48, "Depositing rime fog"),
            Map.entry(51, "Light drizzle"),
            Map.entry(53, "Moderate drizzle"),
            Map.entry(55, "Dense drizzle"),
            Map.entry(61, "Slight rain"),
            Map.entry(63, "Moderate rain"),
            Map.entry(65, "Heavy rain"),
            Map.entry(80, "Slight rain showers"),
            Map.entry(81, "Moderate rain showers"),
            Map.entry(82, "Violent rain showers"),
            Map.entry(95, "Thunderstorm"),
            Map.entry(96, "Thunderstorm with slight hail"),
            Map.entry(99, "Thunderstorm with heavy hail")
    );

    private final RestTemplate restTemplate;

    public WeatherServiceImpl() {
        this.restTemplate = new RestTemplate();
    }

    @Override
    public WeatherResponseDTO getCurrentWeather(WeatherRequestDTO request) {
        String url = String.format(
                "%s?latitude=%f&longitude=%f&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
                OPEN_METEO_URL, request.getLatitude(), request.getLongitude()
        );

        JsonNode response = restTemplate.getForObject(url, JsonNode.class);

        if (response == null || !response.has("current")) {
            return WeatherResponseDTO.builder()
                    .latitude(request.getLatitude())
                    .longitude(request.getLongitude())
                    .timestamp(LocalDateTime.now())
                    .build();
        }

        JsonNode current = response.get("current");
        int weatherCode = current.has("weather_code") ? current.get("weather_code").asInt() : 0;

        return WeatherResponseDTO.builder()
                .latitude(request.getLatitude())
                .longitude(request.getLongitude())
                .timestamp(LocalDateTime.now())
                .temperature(current.has("temperature_2m") ? current.get("temperature_2m").asDouble() : null)
                .precipitation(current.has("precipitation") ? current.get("precipitation").asDouble() : null)
                .humidity(current.has("relative_humidity_2m") ? current.get("relative_humidity_2m").asDouble() : null)
                .windSpeed(current.has("wind_speed_10m") ? current.get("wind_speed_10m").asDouble() : null)
                .weatherCode(weatherCode)
                .weatherDescription(WEATHER_CODES.getOrDefault(weatherCode, "Unknown"))
                .build();
    }
}
