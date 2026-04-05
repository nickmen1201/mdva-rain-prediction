package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import ti.mdva.model.dto.WeatherRequestDTO;
import ti.mdva.model.dto.WeatherResponseDTO;
import ti.mdva.service.WeatherService;

/**
 * Controller for weather data endpoints using Open-Meteo API.
 */
@RestController
@RequestMapping("/api/weather")
@Tag(name = "Weather", description = "Weather data endpoints using Open-Meteo API")
public class WeatherController {

    private final WeatherService weatherService;

    public WeatherController(WeatherService weatherService) {
        this.weatherService = weatherService;
    }

    @PostMapping("/current")
    @Operation(summary = "Get current weather", description = "Fetches current weather data for specified coordinates")
    public ResponseEntity<WeatherResponseDTO> getCurrentWeather(@Valid @RequestBody WeatherRequestDTO request) {
        return ResponseEntity.ok(weatherService.getCurrentWeather(request));
    }

    @GetMapping("/current")
    @Operation(summary = "Get current weather by coordinates", description = "Fetches current weather using query parameters")
    public ResponseEntity<WeatherResponseDTO> getCurrentWeatherByCoords(
            @RequestParam double latitude,
            @RequestParam double longitude) {
        WeatherRequestDTO request = new WeatherRequestDTO();
        request.setLatitude(latitude);
        request.setLongitude(longitude);
        return ResponseEntity.ok(weatherService.getCurrentWeather(request));
    }
}
