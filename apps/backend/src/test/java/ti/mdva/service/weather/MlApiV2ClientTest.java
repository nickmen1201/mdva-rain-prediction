package ti.mdva.service.weather;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.List;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

@DisplayName("MlApiV2Client — lote, monitoreo y errores explícitos (spec 007)")
class MlApiV2ClientTest {

    private static final String BASE = "http://ml:8081";
    private static final HourlyInputs ENTRADA = new HourlyInputs(
            Instant.parse("2026-10-29T15:00:00Z"), 20.0, 75.0, 15.5, 60.0, 2.0, 180.0, 1013.0, 0.4, 120.0);
    private static final String AMARILLO = "{\"probability\": 0.5, \"alert_level\": \"AMARILLO\"}";

    private MockRestServiceServer server;
    private MlApiV2Client client;

    @BeforeEach
    void setup() {
        RestTemplate rt = new RestTemplate();
        server = MockRestServiceServer.bindTo(rt).build();
        client = new MlApiV2Client(rt, BASE);
    }

    private static String predicciones(int n) {
        return "{\"predictions\": [" + IntStream.range(0, n).mapToObj(i -> AMARILLO).collect(Collectors.joining(",")) + "]}";
    }

    @Test
    @DisplayName("predictBatch envía los registros con los nombres del contrato y conserva el orden")
    void lote() {
        server.expect(requestTo(BASE + "/v2/predict/batch"))
                .andExpect(method(POST))
                .andExpect(jsonPath("$.records.length()").value(2))
                .andExpect(jsonPath("$.records[0].time_utc").value("2026-10-29T15:00:00Z"))
                .andExpect(jsonPath("$.records[0].wind_speed_10m").value(2.0))
                .andExpect(jsonPath("$.records[0].cape").value(120.0))
                .andRespond(withSuccess("""
                        {"predictions": [{"probability": 0.12, "alert_level": "VERDE"},
                                         {"probability": 0.81, "alert_level": "ROJO"}]}""",
                        MediaType.APPLICATION_JSON));

        List<MlApiV2Client.Prediction> p = client.predictBatch(List.of(ENTRADA, ENTRADA));

        server.verify();
        assertThat(p).containsExactly(
                new MlApiV2Client.Prediction(0.12, "VERDE"), new MlApiV2Client.Prediction(0.81, "ROJO"));
    }

    @Test
    @DisplayName("Más de 200 entradas se parten en lotes del máximo permitido")
    void loteGrandeSeParte() {
        server.expect(requestTo(BASE + "/v2/predict/batch"))
                .andExpect(jsonPath("$.records.length()").value(MlApiV2Client.MAX_BATCH))
                .andRespond(withSuccess(predicciones(MlApiV2Client.MAX_BATCH), MediaType.APPLICATION_JSON));
        server.expect(requestTo(BASE + "/v2/predict/batch"))
                .andExpect(jsonPath("$.records.length()").value(1))
                .andRespond(withSuccess(predicciones(1), MediaType.APPLICATION_JSON));

        List<MlApiV2Client.Prediction> p = client.predictBatch(
                IntStream.range(0, MlApiV2Client.MAX_BATCH + 1).mapToObj(i -> ENTRADA).toList());

        server.verify();
        assertThat(p).hasSize(MlApiV2Client.MAX_BATCH + 1);
    }

    @Test
    @DisplayName("monitorTrip envía la probabilidad inicial y el instante UTC del dato")
    void monitoreo() {
        server.expect(requestTo(BASE + "/v2/monitor/trip"))
                .andExpect(method(POST))
                .andExpect(jsonPath("$.probability_start").value(0.3))
                .andExpect(jsonPath("$.weather_timestamp_utc").value("2026-10-29T14:00:00Z"))
                .andExpect(jsonPath("$.current.time_utc").value("2026-10-29T15:00:00Z"))
                .andRespond(withSuccess("""
                        {"probability_now": 0.62, "delta": 0.32, "latency_minutes": 60,
                         "stale_data": true, "change_level": "SIGNIFICATIVO", "model_version": "1.0.0"}""",
                        MediaType.APPLICATION_JSON));

        MlApiV2Client.MonitorResult r = client.monitorTrip(
                0.3, OffsetDateTime.of(2026, 10, 29, 9, 0, 0, 0, ZoneOffset.ofHours(-5)), ENTRADA);

        server.verify();
        assertThat(r).isEqualTo(new MlApiV2Client.MonitorResult(0.62, 0.32, 60, true, "SIGNIFICATIVO"));
    }

    @Test
    @DisplayName("422 Problem Details: error explícito con el detalle, nunca una probabilidad por defecto")
    void rechazo422() {
        server.expect(requestTo(BASE + "/v2/predict/batch"))
                .andRespond(withStatus(HttpStatus.UNPROCESSABLE_ENTITY)
                        .contentType(MediaType.APPLICATION_PROBLEM_JSON)
                        .body("{\"title\": \"Entrada inválida\", \"status\": 422, \"detail\": \"cape fuera de rango\"}"));

        assertThatThrownBy(() -> client.predictBatch(List.of(ENTRADA)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("422")
                .hasMessageContaining("cape fuera de rango");
    }

    @Test
    @DisplayName("Menos predicciones que entradas: error explícito")
    void respuestaIncompleta() {
        server.expect(requestTo(BASE + "/v2/predict/batch"))
                .andRespond(withSuccess(predicciones(1), MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.predictBatch(List.of(ENTRADA, ENTRADA)))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("1 predicciones para 2 entradas");
    }
}
