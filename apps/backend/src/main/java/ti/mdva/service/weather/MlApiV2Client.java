package ti.mdva.service.weather;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.time.OffsetDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Cliente del ML API v2 (contrato: specs/006-ml-api-v2/contracts/openapi-v2.yaml).
 * Un rechazo de entrada (422 Problem Details) se convierte en error explícito; nunca en
 * una probabilidad por defecto.
 */
@Component
public class MlApiV2Client {

    /** Máximo de registros por petición del endpoint por lotes. */
    static final int MAX_BATCH = 200;

    public record Prediction(double probability, String alertLevel) {}

    public record MonitorResult(
            double probabilityNow, double delta, int latencyMinutes, boolean staleData, String changeLevel) {}

    private final RestTemplate restTemplate;
    private final String baseUrl;

    @Autowired
    public MlApiV2Client(RestTemplateBuilder builder, @Value("${ml.service.url}") String baseUrl) {
        // HTTP/1.1 explícito: el cliente JDK por defecto intenta "Upgrade: h2c" y uvicorn descarta el cuerpo
        this(builder.requestFactory(SimpleClientHttpRequestFactory.class)
                .connectTimeout(Duration.ofSeconds(5)).readTimeout(Duration.ofSeconds(15)).build(), baseUrl);
    }

    MlApiV2Client(RestTemplate restTemplate, String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    /** Una predicción por entrada, en el mismo orden (en lotes de hasta 200). */
    public List<Prediction> predictBatch(List<HourlyInputs> entradas) {
        List<Prediction> out = new ArrayList<>(entradas.size());
        for (int i = 0; i < entradas.size(); i += MAX_BATCH) {
            List<Map<String, Object>> records = entradas.subList(i, Math.min(i + MAX_BATCH, entradas.size()))
                    .stream().map(HourlyInputs::toModelRecord).toList();
            JsonNode body = post("/v2/predict/batch", Map.of("records", records));
            for (JsonNode p : body.path("predictions")) {
                out.add(new Prediction(p.path("probability").asDouble(), p.path("alert_level").asText()));
            }
        }
        if (out.size() != entradas.size()) {
            throw new IllegalStateException(
                    "El ML API devolvió %d predicciones para %d entradas".formatted(out.size(), entradas.size()));
        }
        return out;
    }

    public MonitorResult monitorTrip(double probabilityStart, OffsetDateTime weatherTimestamp, HourlyInputs current) {
        JsonNode r = post("/v2/monitor/trip", Map.of(
                "probability_start", probabilityStart,
                "weather_timestamp_utc", weatherTimestamp.toInstant().toString(),
                "current", current.toModelRecord()));
        return new MonitorResult(
                r.path("probability_now").asDouble(),
                r.path("delta").asDouble(),
                r.path("latency_minutes").asInt(),
                r.path("stale_data").asBoolean(),
                r.path("change_level").asText());
    }

    private JsonNode post(String path, Object body) {
        try {
            JsonNode r = restTemplate.postForObject(baseUrl + path, body, JsonNode.class);
            if (r == null) throw new IllegalStateException("El ML API no respondió en " + path);
            return r;
        } catch (HttpClientErrorException e) {
            throw new IllegalStateException(
                    "El ML API rechazó la petición a %s (%d): %s".formatted(path, e.getStatusCode().value(),
                            e.getResponseBodyAsString()), e);
        }
    }
}
