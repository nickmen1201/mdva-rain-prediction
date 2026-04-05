package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;
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
 * Flujo exacto documentado en el TODO de ViajeUseCase.java:
 *  1. GET Open-Meteo → temperatura, humedad, nubosidad, viento para hora actual
 *  2. POST FastAPI /predecir/ambos → predicción de lluvia de ambos modelos
 *  3. Retorna RainPredictionDTO con el resultado consolidado
 *
 * Configurar en application.yml:
 *   ml.service.url: http://localhost:8081   (o URL del contenedor FastAPI)
 */
@Slf4j
@Service
public class WeatherMLServiceImpl implements WeatherMLService {

    private static final String OPEN_METEO_URL =
        "https://api.open-meteo.com/v1/forecast" +
        "?latitude=%f&longitude=%f" +
        "&hourly=temperature_2m,relativehumidity_2m,cloudcover,windspeed_10m" +
        "&current_weather=true" +
        "&timezone=America%%2FBogota";

    private final RestTemplate restTemplate;
    private final String mlServiceUrl;

    public WeatherMLServiceImpl(@Value("${ml.service.url}") String mlServiceUrl) {
        this.restTemplate = new RestTemplate();
        this.mlServiceUrl = mlServiceUrl;
    }

    @Override
    public RainPredictionDTO predictRainForLocation(double lat, double lng) {
        // ── Paso 1: Obtener variables climáticas de Open-Meteo ────────────────
        String weatherUrl = String.format(OPEN_METEO_URL, lat, lng);
        JsonNode weatherResponse = restTemplate.getForObject(weatherUrl, JsonNode.class);

        if (weatherResponse == null) {
            throw new RuntimeException("Open-Meteo no respondió para lat=%f, lng=%f".formatted(lat, lng));
        }

        LocalDateTime now = LocalDateTime.now();
        int currentHour   = now.getHour();
        int currentMonth  = now.getMonthValue();

        // Buscar el índice de la hora actual en el array hourly
        JsonNode hourlyTimes = weatherResponse.path("hourly").path("time");
        int idx = findHourIndex(hourlyTimes, now);

        JsonNode hourly = weatherResponse.path("hourly");
        double tempC        = hourly.path("temperature_2m").get(idx).asDouble();
        double humidityPct  = hourly.path("relativehumidity_2m").get(idx).asDouble();
        double cloudPct     = hourly.path("cloudcover").get(idx).asDouble();
        // Open-Meteo entrega windspeed en km/h → convertir a m/s
        double windKmh      = hourly.path("windspeed_10m").get(idx).asDouble();
        double windMs       = Math.round((windKmh / 3.6) * 100.0) / 100.0;

        log.debug("Open-Meteo [hora={}]: temp={}°C hum={}% nub={}% viento={}m/s",
                currentHour, tempC, humidityPct, cloudPct, windMs);

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
        double probRf = 0.0, probRl = 0.0;
        boolean anyRain = false;

        for (JsonNode pred : mlResponse.getBody()) {
            String modelo = pred.path("modelo").asText();
            double prob   = pred.path("probabilidad_lluvia").asDouble();
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
     * Busca en el array de tiempos de Open-Meteo (formato "yyyy-MM-ddTHH")
     * el índice correspondiente a la hora actual.
     * Fallback: retorna el índice de la hora actual del día (0-23).
     */
    private int findHourIndex(JsonNode timesNode, LocalDateTime now) {
        String target = now.toString().substring(0, 13); // "yyyy-MM-ddTHH"
        if (timesNode.isArray()) {
            for (int i = 0; i < timesNode.size(); i++) {
                if (timesNode.get(i).asText().startsWith(target)) {
                    return i;
                }
            }
        }
        // Fallback: el índice coincide con la hora del día
        return now.getHour();
    }
}
