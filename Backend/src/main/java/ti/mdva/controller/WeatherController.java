package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ti.mdva.model.dto.WeatherRequestDTO;
import ti.mdva.model.dto.WeatherResponseDTO;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.WeatherService;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.stream.Collectors;

/**
 * Controller for weather data and heatmap endpoints.
 */
@RestController
@RequestMapping("/api/weather")
@Tag(name = "Weather", description = "Weather data endpoints")
public class WeatherController {

    private final WeatherService weatherService;
    private final WeatherMLService weatherMLService;

    public WeatherController(WeatherService weatherService, WeatherMLService weatherMLService) {
        this.weatherService   = weatherService;
        this.weatherMLService = weatherMLService;
    }

    @PostMapping("/current")
    @Operation(summary = "Get current weather by coordinates (body)")
    public ResponseEntity<WeatherResponseDTO> getCurrentWeather(@Valid @RequestBody WeatherRequestDTO request) {
        return ResponseEntity.ok(weatherService.getCurrentWeather(request));
    }

    @GetMapping("/current")
    @Operation(summary = "Get current weather by coordinates (params)")
    public ResponseEntity<WeatherResponseDTO> getCurrentWeatherByCoords(
            @RequestParam double latitude,
            @RequestParam double longitude) {
        WeatherRequestDTO request = new WeatherRequestDTO();
        request.setLatitude(latitude);
        request.setLongitude(longitude);
        return ResponseEntity.ok(weatherService.getCurrentWeather(request));
    }

    /**
     * Sprint 5.2B: Predice probabilidad de lluvia para un grid de puntos (heatmap).
     * Llama al ML en paralelo para cada punto del grid.
     *
     * Request:  { "puntos": [{ "lat": 6.21, "lng": -75.58 }, ...] }
     * Response: { "resultados": [{ "lat": 6.21, "lng": -75.58, "probabilidadRf": 0.72 }, ...] }
     */
    @PostMapping("/predict-grid")
    @Operation(summary = "Predict rain probability for a grid of lat/lng points (used for heatmap layer)")
    public ResponseEntity<Map<String, List<GridResultado>>> predictGrid(
            @RequestBody Map<String, List<Map<String, Double>>> body
    ) {
        List<Map<String, Double>> puntos = body.getOrDefault("puntos", List.of());

        List<CompletableFuture<GridResultado>> futures = puntos.stream()
            .map(p -> CompletableFuture.supplyAsync(() -> {
                double lat = p.getOrDefault("lat", 6.2442);
                double lng = p.getOrDefault("lng", -75.5812);
                try {
                    var pred = weatherMLService.predictRainForLocation(lat, lng);
                    return new GridResultado(lat, lng, pred.getProbabilidadRf() != null ? pred.getProbabilidadRf() : 0.0);
                } catch (Exception e) {
                    return new GridResultado(lat, lng, 0.0);
                }
            }))
            .toList();

        List<GridResultado> resultados = futures.stream()
            .map(CompletableFuture::join)
            .collect(Collectors.toList());

        return ResponseEntity.ok(Map.of("resultados", resultados));
    }

    /** Resultado para un punto del grid de heatmap. */
    public record GridResultado(double lat, double lng, double probabilidadRf) {}
}
