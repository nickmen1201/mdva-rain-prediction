package ti.mdva.service.weather;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.time.Instant;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.hamcrest.Matchers.startsWith;
import static org.springframework.http.HttpMethod.GET;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.queryParam;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

@DisplayName("OpenMeteoForecastClient — 9 variables, UTC y unidades verificadas (spec 007)")
class OpenMeteoForecastClientTest {

    private static final String URL = "https://api.open-meteo.com/v1/forecast";

    private static final String UNIDADES = """
            "hourly_units": {"time": "iso8601", "temperature_2m": "°C", "relative_humidity_2m": "%",
              "dew_point_2m": "°C", "cloud_cover": "%", "wind_speed_10m": "m/s", "wind_direction_10m": "°",
              "pressure_msl": "hPa", "precipitation": "mm", "cape": "J/kg"}""";

    private MockRestServiceServer server;
    private OpenMeteoForecastClient client;

    @BeforeEach
    void setup() {
        RestTemplate rt = new RestTemplate();
        server = MockRestServiceServer.bindTo(rt).build();
        client = new OpenMeteoForecastClient(rt, URL);
    }

    private static String ubicacion(String unidades, String temperaturas) {
        return """
                {%s,
                 "hourly": {"time": ["2026-10-29T14:00", "2026-10-29T15:00", "2026-10-29T16:00"],
                   "temperature_2m": %s, "relative_humidity_2m": [80, 81, 82], "dew_point_2m": [15, 15, 15],
                   "cloud_cover": [90, 95, 100], "wind_speed_10m": [1.5, 2.0, 2.5], "wind_direction_10m": [180, 190, 200],
                   "pressure_msl": [1012, 1013, 1014], "precipitation": [0.0, 0.4, 1.2], "cape": [100, 200, 300]}}
                """.formatted(unidades, temperaturas);
    }

    @Test
    @DisplayName("Pide las 9 variables en UTC con unidades explícitas y parsea las horas como instantes UTC")
    void unaUbicacion() {
        server.expect(requestTo(startsWith(URL)))
                .andExpect(method(GET))
                .andExpect(queryParam("latitude", "6.24420"))
                .andExpect(queryParam("longitude", "-75.58120"))
                .andExpect(queryParam("hourly", String.join(",", OpenMeteoForecastClient.VARIABLES)))
                .andExpect(queryParam("timezone", "GMT"))
                .andExpect(queryParam("wind_speed_unit", "ms"))
                .andExpect(queryParam("temperature_unit", "celsius"))
                .andExpect(queryParam("precipitation_unit", "mm"))
                .andRespond(withSuccess(ubicacion(UNIDADES, "[20.1, 21.2, 22.3]"), MediaType.APPLICATION_JSON));

        List<HourlyInputs> serie = client.hourly(6.2442, -75.5812);

        server.verify();
        assertThat(serie).hasSize(3);
        HourlyInputs h = serie.get(1);
        assertThat(h.timeUtc()).isEqualTo(Instant.parse("2026-10-29T15:00:00Z"));
        assertThat(h.temperature2m()).isEqualTo(21.2);
        assertThat(h.windSpeed10m()).isEqualTo(2.0);
        assertThat(h.precipitation()).isEqualTo(0.4);
        assertThat(h.cape()).isEqualTo(200.0);
    }

    @Test
    @DisplayName("Varias ubicaciones en una sola llamada, en el mismo orden")
    void variasUbicaciones() {
        String cuerpo = "[" + ubicacion(UNIDADES, "[10, 11, 12]") + "," + ubicacion(UNIDADES, "[30, 31, 32]") + "]";
        server.expect(requestTo(startsWith(URL)))
                .andExpect(queryParam("latitude", "6.20000,6.30000"))
                .andExpect(queryParam("longitude", "-75.50000,-75.60000"))
                .andRespond(withSuccess(cuerpo, MediaType.APPLICATION_JSON));

        List<List<HourlyInputs>> series = client.hourly(List.of(new double[]{6.2, -75.5}, new double[]{6.3, -75.6}));

        server.verify();
        assertThat(series).hasSize(2);
        assertThat(series.get(0).get(0).temperature2m()).isEqualTo(10.0);
        assertThat(series.get(1).get(0).temperature2m()).isEqualTo(30.0);
    }

    @Test
    @DisplayName("Unidades declaradas distintas a las pedidas: falla, nunca convierte en silencio")
    void unidadesInesperadas() {
        server.expect(requestTo(startsWith(URL)))
                .andRespond(withSuccess(ubicacion(UNIDADES.replace("m/s", "km/h"), "[20, 21, 22]"),
                        MediaType.APPLICATION_JSON));

        assertThatThrownBy(() -> client.hourly(6.2442, -75.5812))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("wind_speed_10m");
    }

    @Test
    @DisplayName("Horas con valores nulos se omiten (no se rellenan)")
    void horasIncompletasSeOmiten() {
        server.expect(requestTo(startsWith(URL)))
                .andRespond(withSuccess(ubicacion(UNIDADES, "[20, null, 22]"), MediaType.APPLICATION_JSON));

        List<HourlyInputs> serie = client.hourly(6.2442, -75.5812);

        assertThat(serie).extracting(HourlyInputs::timeUtc).containsExactly(
                Instant.parse("2026-10-29T14:00:00Z"), Instant.parse("2026-10-29T16:00:00Z"));
    }

    @Test
    @DisplayName("Hora en curso: la primera hora con inicio ≥ el instante pedido")
    void horaEnCurso() {
        server.expect(requestTo(startsWith(URL)))
                .andRespond(withSuccess(ubicacion(UNIDADES, "[20, 21, 22]"), MediaType.APPLICATION_JSON));
        List<HourlyInputs> serie = client.hourly(6.2442, -75.5812);

        assertThat(OpenMeteoForecastClient.from(serie, Instant.parse("2026-10-29T15:00:00Z"), 1))
                .extracting(HourlyInputs::temperature2m).containsExactly(21.0);
        assertThat(OpenMeteoForecastClient.from(serie, Instant.parse("2026-10-29T14:30:00Z"), 5))
                .extracting(HourlyInputs::temperature2m).containsExactly(21.0, 22.0);
    }
}
