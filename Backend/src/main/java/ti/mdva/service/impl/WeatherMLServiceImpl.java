package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.service.WeatherMLService;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Implementación de WeatherMLService.
 *
 * Flujo:
 *  1. GET Google Weather API /currentConditions:lookup
 *       → temperatura (°C), humedad (%), cobertura nubosa (%), viento (km/h → m/s)
 *  2. POST FastAPI /predecir/ambos → predicción de lluvia de ambos modelos ML
 *  3. Retorna RainPredictionDTO con el resultado consolidado
 *
 * Documentación: https://developers.google.com/maps/documentation/weather/current-conditions
 */
@Service
public class WeatherMLServiceImpl implements WeatherMLService {

    private static final Logger log = LoggerFactory.getLogger(WeatherMLServiceImpl.class);

    private static final String GOOGLE_WEATHER_URL =
        "https://weather.googleapis.com/v1/currentConditions:lookup" +
        "?key=%s" +
        "&location.latitude=%f" +
        "&location.longitude=%f" +
        "&unitsSystem=METRIC";

    private final RestTemplate restTemplate;
    private final String mlServiceUrl;
    private final String googleApiKey;

    public WeatherMLServiceImpl(
            @Value("${ml.service.url}")      String mlServiceUrl,
            @Value("${google.maps.api-key}") String googleApiKey
    ) {
        this.restTemplate = new RestTemplate();
        this.mlServiceUrl = mlServiceUrl;
        this.googleApiKey = googleApiKey;
    }

    @Override
    public RainPredictionDTO predictRainForLocation(double lat, double lng) {

        // ── Paso 1: Condiciones actuales desde Google Weather API ─────────────
        String weatherUrl = String.format(GOOGLE_WEATHER_URL, googleApiKey, lat, lng);
        JsonNode weather  = restTemplate.getForObject(weatherUrl, JsonNode.class);

        if (weather == null) {
            throw new RuntimeException(
                "Google Weather API no respondió para lat=%.4f, lng=%.4f".formatted(lat, lng));
        }

        double tempC       = weather.path("temperature").path("degrees").asDouble();
        double humidityPct = weather.path("relativeHumidity").asDouble();
        double cloudPct    = inferCloudCover(weather);
        double windKmh     = weather.path("wind").path("speed").path("value").asDouble();
        double windMs      = Math.round((windKmh / 3.6) * 100.0) / 100.0;
        double rainProbPct = weather.path("precipitation").path("probability").path("percent").asDouble();

        LocalDateTime now         = LocalDateTime.now();
        int           currentHour = now.getHour();
        int           currentMonth= now.getMonthValue();

        log.debug("Google Weather [lat={}, lng={}]: temp={}C hum={}% nub={}% viento={}m/s lluvia={}%",
                lat, lng, tempC, humidityPct, cloudPct, windMs, rainProbPct);

        // ── Paso 2: Enviar al microservicio FastAPI ML ────────────────────────
        Map<String, Object> mlPayload = Map.of(
            "temperatura_c",         tempC,
            "humedad_relativa_pct",  humidityPct,
            "cobertura_nubosa_pct",  cloudPct,
            "velocidad_viento_ms",   windMs,
            "hora",                  currentHour,
            "mes",                   currentMonth
        );

        String mlEndpoint = mlServiceUrl + "/predecir/ambos";
        ResponseEntity<JsonNode[]> mlResponse =
            restTemplate.postForEntity(mlEndpoint, mlPayload, JsonNode[].class);

        if (mlResponse.getBody() == null || mlResponse.getBody().length == 0) {
            throw new RuntimeException("El microservicio ML no retornó predicciones");
        }

        // ── Paso 3: Consolidar resultado ──────────────────────────────────────
        // Fallback inicial: usar probabilidad de lluvia directa de Google
        double  probRf  = rainProbPct / 100.0;
        double  probRl  = rainProbPct / 100.0;
        boolean anyRain = rainProbPct > 40;

        for (JsonNode pred : mlResponse.getBody()) {
            String  modelo = pred.path("modelo").asText();
            double  prob   = pred.path("probabilidad_lluvia").asDouble();
            boolean llueve = pred.path("llueve").asBoolean();
            anyRain = anyRain || llueve;

            if ("random_forest".equals(modelo))       probRf = prob;
            if ("regresion_logistica".equals(modelo)) probRl = prob;
        }

        log.debug("ML result: llueve={} RF={} RL={}", anyRain, probRf, probRl);

        return RainPredictionDTO.builder()
                .llueve(anyRain)
                .probabilidadRf(probRf)
                .probabilidadRl(probRl)
                .temperaturaC(tempC)
                .humedadPct(humidityPct)
                .coberturaAnubosaPct(cloudPct)
                .velocidadVientoMs(windMs)
                .build();
    }

    /**
     * Infiere cobertura nubosa (%) desde el tipo de condición de Google Weather.
     * currentConditions no expone cloudCover directamente, solo en forecast/hours.
     */
    private double inferCloudCover(JsonNode weather) {
        String type = weather.path("weatherCondition").path("type").asText("");
        return switch (type) {
            case "CLEAR", "SUNNY"                            -> 0.0;
            case "MOSTLY_CLEAR", "MOSTLY_SUNNY"              -> 15.0;
            case "PARTLY_CLOUDY", "PARTLY_SUNNY"             -> 40.0;
            case "MOSTLY_CLOUDY", "HAZE", "HAZY_MOONLIGHT"  -> 70.0;
            case "CLOUDY", "OVERCAST"                        -> 90.0;
            case "FOG", "FOGGY"                              -> 85.0;
            case "DRIZZLE", "LIGHT_RAIN", "RAIN",
                 "RAIN_SHOWERS", "HEAVY_RAIN"                -> 95.0;
            case "THUNDERSTORM", "STRONG_THUNDERSTORM",
                 "THUNDERSHOWER"                             -> 100.0;
            case "SNOW", "FLURRIES", "BLIZZARD"              -> 90.0;
            default                                          -> 50.0;
        };
    }
}