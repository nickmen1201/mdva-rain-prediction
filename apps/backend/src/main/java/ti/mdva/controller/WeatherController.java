package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ti.mdva.model.dto.BestWindowDTO;
import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.service.BestWindowAnalyzer;
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
     * HU014 (Sprint 3): variables ambientales actuales + predicción de lluvia
     * para un punto específico. Endpoint atómico para clientes ligeros que solo
     * necesitan el clima actual sin planificar un viaje.
     *
     * Ejemplo: GET /api/weather/current?latitude=6.2442&longitude=-75.5812
     */
    @GetMapping("/current")
    @Operation(
        summary = "Variables ambientales actuales + predicción de lluvia (HU014)",
        description = "Pipeline: Open-Meteo (hora UTC en curso, 9 variables del contrato de features) → ML API v2 (rain_classifier). Incluye el instante UTC del dato."
    )
    public ResponseEntity<RainPredictionDTO> getCurrent(
            @RequestParam double latitude,
            @RequestParam double longitude
    ) {
        return ResponseEntity.ok(weatherMLService.predictRainForLocation(latitude, longitude));
    }

    /**
     * Sprint 5.2B: Predice probabilidad de lluvia para un grid de puntos (heatmap).
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

    public record GridResultado(double lat, double lng, double probabilidadRf) {}

    /**
     * Punto 5 feedback: predicción horaria del clima para las próximas N horas.
     * Pipeline: Open-Meteo Hourly (gratis) → modelo ML local (random_forest) por hora.
     *
     * Ejemplo: GET /api/weather/forecast?latitude=6.2442&longitude=-75.5812&hours=6
     */
    @GetMapping("/forecast")
    @Operation(summary = "Predicción horaria de lluvia (Open-Meteo + ML local) para las próximas N horas")
    public ResponseEntity<List<HourlyForecastDTO>> getHourlyForecast(
            @RequestParam double latitude,
            @RequestParam double longitude,
            @RequestParam(defaultValue = "6") int hours
    ) {
        return ResponseEntity.ok(weatherMLService.getHourlyForecast(latitude, longitude, hours));
    }

    /**
     * Recomienda la mejor ventana horaria para salir según el forecast horario.
     * Cubre la propuesta inicial: "Recomendaciones de horarios con menor probabilidad de lluvia".
     *
     * Ejemplo: GET /api/weather/best-window?latitude=6.2442&longitude=-75.5812&hours=6
     */
    @GetMapping("/best-window")
    @Operation(
        summary = "Mejor horario para salir en las próximas N horas",
        description = "Analiza el forecast horario y devuelve la hora de menor probabilidad de lluvia con un mensaje instructivo."
    )
    public ResponseEntity<BestWindowDTO> getBestWindow(
            @RequestParam double latitude,
            @RequestParam double longitude,
            @RequestParam(defaultValue = "6") int hours
    ) {
        var forecast = weatherMLService.getHourlyForecast(latitude, longitude, hours);
        return ResponseEntity.ok(BestWindowAnalyzer.analizar(forecast));
    }
}
