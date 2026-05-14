package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.service.WeatherMLService;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/weather")
@Tag(name = "Weather", description = "Weather data endpoints")
public class WeatherController {

    private final WeatherMLService weatherMLService;

    public WeatherController(WeatherMLService weatherMLService) {
        this.weatherMLService = weatherMLService;
    }

    /**
     * Predice probabilidad de lluvia para una grilla de puntos del heatmap.
     *
     * Request:  { "puntos": [{ "lat": 6.21, "lng": -75.58 }, ...] }
     * Response: { "resultados": [{ "lat": 6.21, "lng": -75.58, "probabilidadRf": 0.72 }], ... }
     */
    @PostMapping("/predict-grid")
    @Operation(summary = "Predict rain probability for a grid of lat/lng points")
    public ResponseEntity<WeatherGridResponseDTO> predictGrid(
            @RequestBody Map<String, List<Map<String, Double>>> body
    ) {
        List<WeatherGridPointDTO> puntos = body.getOrDefault("puntos", List.of()).stream()
            .map(p -> new WeatherGridPointDTO(
                p.getOrDefault("lat", 6.2442),
                p.getOrDefault("lng", -75.5812)
            ))
            .toList();

        return ResponseEntity.ok(weatherMLService.predictGridForArea(puntos));
    }
}
