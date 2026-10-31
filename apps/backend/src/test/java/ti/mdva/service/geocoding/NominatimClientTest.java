package ti.mdva.service.geocoding;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.ExpectedCount;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.queryParam;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;
import static org.hamcrest.Matchers.startsWith;

@DisplayName("NominatimClient — política de uso, caché y limitador (spec 008)")
class NominatimClientTest {

    private static final String BASE = "https://nominatim.test";
    private static final String UA = "MDVA-test/1.0 (+https://example.org)";
    private static final String EXPLORA = """
            [{"display_name": "Parque Explora, Carrera 52, Medellín", "lat": "6.2706", "lon": "-75.5658",
              "type": "museum"}]""";

    /** Reloj manual: el *sleeper* avanza el tiempo en lugar de dormir. */
    private static final class ManualClock extends Clock {
        Instant now = Instant.parse("2026-10-31T12:00:00Z");

        @Override public ZoneOffset getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(java.time.ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }

    private ManualClock clock;
    private List<Duration> sleeps;
    private MockRestServiceServer server;
    private NominatimClient client;

    @BeforeEach
    void setup() {
        clock = new ManualClock();
        sleeps = new ArrayList<>();
        RestTemplate rt = new RestTemplate();
        server = MockRestServiceServer.bindTo(rt).build();
        client = new NominatimClient(rt, BASE, UA, clock, d -> {
            sleeps.add(d);
            clock.now = clock.now.plus(d);
        });
    }

    @Test
    @DisplayName("búsqueda limitada al valle, con User-Agent propio, y mapeo de resultados")
    void busqueda() {
        server.expect(requestTo(startsWith(BASE + "/search")))
                .andExpect(queryParam("q", "Parque%20Explora"))
                .andExpect(queryParam("format", "jsonv2"))
                .andExpect(queryParam("limit", "5"))
                .andExpect(queryParam("countrycodes", "co"))
                .andExpect(queryParam("viewbox", NominatimClient.VIEWBOX))
                .andExpect(queryParam("bounded", "1"))
                .andExpect(header("User-Agent", UA))
                .andRespond(withSuccess(EXPLORA, MediaType.APPLICATION_JSON));

        List<GeocodingResultDTO> r = client.search("Parque Explora");

        assertThat(r).containsExactly(new GeocodingResultDTO("Parque Explora, Carrera 52, Medellín", 6.2706, -75.5658, "museum"));
        server.verify();
    }

    @Test
    @DisplayName("la misma búsqueda (normalizada) dentro de 24 h sale de caché; vencida vuelve a consultar")
    void cache() {
        server.expect(ExpectedCount.twice(), requestTo(startsWith(BASE + "/search")))
                .andRespond(withSuccess(EXPLORA, MediaType.APPLICATION_JSON));

        client.search("Parque Explora");
        client.search("  parque   EXPLORÁ ");
        clock.now = clock.now.plus(Duration.ofHours(25));
        client.search("Parque Explora");

        server.verify();
    }

    @Test
    @DisplayName("consultas distintas seguidas se espacian ≥ 1 s (≤ 1 req/s)")
    void limitador() {
        server.expect(ExpectedCount.times(3), requestTo(startsWith(BASE + "/search")))
                .andRespond(withSuccess("[]", MediaType.APPLICATION_JSON));

        client.search("calle 10");
        clock.now = clock.now.plusMillis(300);
        client.search("carrera 43a");
        client.search("estadio");

        assertThat(sleeps).containsExactly(Duration.ofMillis(700), Duration.ofSeconds(1));
    }

    @Test
    @DisplayName("texto de menos de 3 caracteres → 400 sin llamar a Nominatim")
    void textoCorto() {
        assertThatThrownBy(() -> client.search("  a ")).isInstanceOf(IllegalArgumentException.class);
        server.verify();
    }

    @Test
    @DisplayName("reverso: dirección legible o vacío si Nominatim responde error")
    void reverso() {
        server.expect(requestTo(startsWith(BASE + "/reverse")))
                .andExpect(queryParam("lat", "6.2706"))
                .andExpect(queryParam("lon", "-75.5658"))
                .andRespond(withSuccess("""
                        {"display_name": "Carrera 52, Medellín", "lat": "6.2706", "lon": "-75.5658", "type": "road"}""",
                        MediaType.APPLICATION_JSON));
        server.expect(requestTo(startsWith(BASE + "/reverse")))
                .andRespond(withSuccess("{\"error\": \"Unable to geocode\"}", MediaType.APPLICATION_JSON));

        assertThat(client.reverse(6.2706, -75.5658)).map(GeocodingResultDTO::displayName)
                .contains("Carrera 52, Medellín");
        assertThat(client.reverse(0.0, 0.0)).isEqualTo(Optional.empty());
    }

    @Test
    @DisplayName("error del proveedor → GeocodingUnavailableException y no se cachea")
    void errorNoSeCachea() {
        server.expect(requestTo(startsWith(BASE + "/search"))).andRespond(withStatus(HttpStatus.SERVICE_UNAVAILABLE));
        server.expect(requestTo(startsWith(BASE + "/search"))).andRespond(withSuccess(EXPLORA, MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.search("Parque Explora")).isInstanceOf(GeocodingUnavailableException.class);
        assertThat(client.search("Parque Explora")).hasSize(1);
    }

    @Test
    @DisplayName("normalización: minúsculas, sin tildes, espacios colapsados")
    void normalizacion() {
        assertThat(NominatimClient.normalize("  Parque  Explorá ")).isEqualTo("parque explora");
        assertThat(NominatimClient.normalize(null)).isEmpty();
    }
}
