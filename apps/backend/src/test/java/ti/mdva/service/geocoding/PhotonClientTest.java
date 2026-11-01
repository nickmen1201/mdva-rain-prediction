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

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.queryParam;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

@DisplayName("PhotonClient — sugerencias mientras se escribe")
class PhotonClientTest {

    private static final String BASE = "https://photon.test";
    private static final String UA = "MDVA-test/1.0 (+https://example.org)";
    private static final String UDEA = """
            {"features": [
              {"geometry": {"coordinates": [-75.5686, 6.2675]},
               "properties": {"name": "Universidad de Antioquia", "street": "Calle 67", "housenumber": "53-108",
                              "district": "La Candelaria", "city": "Medellín", "osm_value": "university"}},
              {"geometry": {"coordinates": [-75.5690, 6.2680]},
               "properties": {"name": "Universidad de Antioquia", "street": "Calle 67", "housenumber": "53-108",
                              "district": "La Candelaria", "city": "Medellín", "osm_value": "university"}},
              {"geometry": {"coordinates": [-75.57, 6.25]}, "properties": {}}
            ]}""";

    private static final class ManualClock extends Clock {
        Instant now = Instant.parse("2026-10-31T12:00:00Z");

        @Override public ZoneOffset getZone() { return ZoneOffset.UTC; }
        @Override public Clock withZone(java.time.ZoneId zone) { return this; }
        @Override public Instant instant() { return now; }
    }

    private ManualClock clock;
    private MockRestServiceServer server;
    private PhotonClient client;

    @BeforeEach
    void setup() {
        clock = new ManualClock();
        RestTemplate rt = new RestTemplate();
        server = MockRestServiceServer.bindTo(rt).build();
        client = new PhotonClient(rt, BASE, UA, clock);
    }

    @Test
    @DisplayName("consulta limitada al valle con sesgo a Medellín; nombre legible, lat/lng y sin duplicados")
    void sugerencias() {
        server.expect(requestTo(startsWith(BASE + "/api/")))
                .andExpect(queryParam("q", "universidad%20de%20ant"))
                .andExpect(queryParam("bbox", PhotonClient.BBOX))
                .andExpect(queryParam("limit", "5"))
                .andExpect(header("User-Agent", UA))
                .andRespond(withSuccess(UDEA, MediaType.APPLICATION_JSON));

        assertThat(client.suggest("universidad de ant")).containsExactly(new GeocodingResultDTO(
                "Universidad de Antioquia, Calle 67 53-108, La Candelaria, Medellín", 6.2675, -75.5686, "university"));
        server.verify();
    }

    @Test
    @DisplayName("el mismo texto normalizado sale de caché durante 30 min")
    void cache() {
        server.expect(ExpectedCount.twice(), requestTo(startsWith(BASE + "/api/")))
                .andRespond(withSuccess(UDEA, MediaType.APPLICATION_JSON));

        client.suggest("Universidad de Ant");
        client.suggest("  universidad  DE ánt ");
        clock.now = clock.now.plus(Duration.ofMinutes(31));
        client.suggest("universidad de ant");

        server.verify();
    }

    @Test
    @DisplayName("texto corto → 400 sin llamar; proveedor caído → GeocodingUnavailableException")
    void errores() {
        assertThatThrownBy(() -> client.suggest(" ab ")).isInstanceOf(IllegalArgumentException.class);
        server.expect(requestTo(startsWith(BASE + "/api/"))).andRespond(withStatus(HttpStatus.BAD_GATEWAY));
        assertThatThrownBy(() -> client.suggest("estadio")).isInstanceOf(GeocodingUnavailableException.class);
    }
}
