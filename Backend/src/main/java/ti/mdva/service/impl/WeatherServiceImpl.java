package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import ti.mdva.dto.WeatherResponseDTO;
import ti.mdva.dto.WeatherResponseDTO.CurrentWeather;
import ti.mdva.dto.WeatherResponseDTO.HourlyForecast;
import ti.mdva.dto.WeatherResponseDTO.RiskLevel;
import ti.mdva.service.WeatherService;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

/**
 * Weather service implementation using Open-Meteo API.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class WeatherServiceImpl implements WeatherService {

    private static final String OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast";
    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public WeatherResponseDTO getCurrentWeather(Double latitude, Double longitude) {
        try {
            String url = buildUrl(latitude, longitude);
            RestTemplate restTemplate = new RestTemplate();
            String response = restTemplate.getForObject(url, String.class);
            return parseResponse(response, latitude, longitude);
        } catch (Exception e) {
            log.error("Error fetching weather: {}", e.getMessage());
            throw new RuntimeException("Failed to retrieve weather data", e);
        }
    }

    private String buildUrl(Double lat, Double lon) {
        return String.format(
                "%s?latitude=%f&longitude=%f&current=temperature_2m,relative_humidity_2m,apparent_temperature," +
                        "precipitation,weather_code,wind_speed_10m,wind_direction_10m" +
                        "&hourly=temperature_2m,precipitation_probability,precipitation&forecast_hours=24&timezone=auto",
                OPEN_METEO_URL, lat, lon);
    }

    private WeatherResponseDTO parseResponse(String response, Double lat, Double lon) throws Exception {
        JsonNode root = objectMapper.readTree(response);
        JsonNode current = root.get("current");
        JsonNode hourly = root.get("hourly");

        CurrentWeather currentWeather = CurrentWeather.builder()
                .temperature(current.get("temperature_2m").asDouble())
                .feelsLike(current.get("apparent_temperature").asDouble())
                .relativeHumidity(current.get("relative_humidity_2m").asInt())
                .precipitation(current.get("precipitation").asDouble())
                .windSpeed(current.get("wind_speed_10m").asDouble())
                .windDirection(current.get("wind_direction_10m").asInt())
                .description(getDescription(current.get("weather_code").asInt()))
                .rainProbability(hourly.get("precipitation_probability").get(0).asInt())
                .riskLevel(calculateRisk(current.get("precipitation").asDouble(), current.get("wind_speed_10m").asDouble()))
                .build();

        List<HourlyForecast> forecast = new ArrayList<>();
        JsonNode times = hourly.get("time");
        JsonNode temps = hourly.get("temperature_2m");
        JsonNode probs = hourly.get("precipitation_probability");
        JsonNode precips = hourly.get("precipitation");

        for (int i = 0; i < Math.min(24, times.size()); i++) {
            forecast.add(HourlyForecast.builder()
                    .time(LocalDateTime.parse(times.get(i).asText(), DateTimeFormatter.ISO_LOCAL_DATE_TIME))
                    .temperature(temps.get(i).asDouble())
                    .rainProbability(probs.get(i).asInt())
                    .precipitation(precips.get(i).asDouble())
                    .riskLevel(calculateRisk(precips.get(i).asDouble(), 0))
                    .build());
        }

        return WeatherResponseDTO.builder()
                .latitude(lat)
                .longitude(lon)
                .timestamp(LocalDateTime.now())
                .current(currentWeather)
                .hourlyForecast(forecast)
                .build();
    }

    private RiskLevel calculateRisk(double precipitation, double wind) {
        if (precipitation > 10 || wind > 50) return RiskLevel.VERY_HIGH;
        if (precipitation > 5 || wind > 30) return RiskLevel.HIGH;
        if (precipitation > 1 || wind > 20) return RiskLevel.MODERATE;
        return RiskLevel.LOW;
    }

    private String getDescription(int code) {
        return switch (code) {
            case 0 -> "Clear sky";
            case 1, 2, 3 -> "Partly cloudy";
            case 45, 48 -> "Fog";
            case 51, 53, 55 -> "Drizzle";
            case 61, 63, 65 -> "Rain";
            case 80, 81, 82 -> "Rain showers";
            case 95, 96, 99 -> "Thunderstorm";
            default -> "Variable conditions";
        };
    }
}
