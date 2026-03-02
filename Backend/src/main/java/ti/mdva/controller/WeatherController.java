package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ti.mdva.dto.WeatherRequestDTO;
import ti.mdva.dto.WeatherResponseDTO;
import ti.mdva.service.WeatherService;

/**
 * Weather data controller.
 *
 * @author MDVA Team
 * @version 1.0
 */
@RestController
@RequestMapping("/api/v1/weather")
@RequiredArgsConstructor
@Tag(name = "Weather", description = "Weather and environmental data endpoints")
public class WeatherController {

    private final WeatherService weatherService;

    @GetMapping
    @Operation(summary = "Get current weather")
    public ResponseEntity<WeatherResponseDTO> getWeather(
            @RequestParam Double latitude,
            @RequestParam Double longitude) {
        return ResponseEntity.ok(weatherService.getCurrentWeather(latitude, longitude));
    }

    @PostMapping
    @Operation(summary = "Get weather by coordinates")
    public ResponseEntity<WeatherResponseDTO> getWeatherPost(@Valid @RequestBody WeatherRequestDTO request) {
        return ResponseEntity.ok(weatherService.getCurrentWeather(request.getLatitude(), request.getLongitude()));
    }
}
