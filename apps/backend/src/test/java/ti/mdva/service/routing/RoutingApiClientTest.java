package ti.mdva.service.routing;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.TripRequestDTO;

import java.io.IOException;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.springframework.http.HttpMethod.POST;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

@DisplayName("RoutingApiClient — /route/spring sin Google (spec 008)")
class RoutingApiClientTest {

    private static final String BASE = "http://routing:8000";
    private static final String URL = BASE + "/api/v1/route/spring";
    private static final LocationPointDTO ORIGEN = punto(6.2502, -75.5684);
    private static final LocationPointDTO DESTINO = punto(6.2088, -75.5672);

    private static final String RESPUESTA = """
            {"distanciaMetros": 5400, "duracionSegundos": 720, "overviewPolyline": "abc",
             "pasos": [{"instruccion": "Continuar hacia el sur por 500 metros", "distanciaMetros": 500,
                        "duracionSegundos": 45, "startLat": 6.25, "startLng": -75.56,
                        "endLat": 6.245, "endLng": -75.565}],
             "rain_factor": 1.8, "mdva_probabilidad_rf": 0.93, "alerta_nivel": "ROJO",
             "alternativas": [{"distanciaMetros": 5400, "duracionSegundos": 720, "overviewPolyline": "abc",
                               "pasos": [], "route_type": "dryest"},
                              {"distanciaMetros": 5100, "duracionSegundos": 760, "overviewPolyline": "xyz",
                               "pasos": [], "route_type": "shortest"}]}""";

    private MockRestServiceServer server;
    private RoutingApiClient client;

    @BeforeEach
    void setup() {
        RestTemplate rt = new RestTemplate();
        server = MockRestServiceServer.bindTo(rt).build();
        client = new RoutingApiClient(rt, BASE);
    }

    private static LocationPointDTO punto(double lat, double lng) {
        return LocationPointDTO.builder().lat(lat).lng(lng).build();
    }

    @Test
    @DisplayName("envía coordenadas, paradas y tipo de vehículo; lee geometría y duración base")
    void rutaConParadas() {
        server.expect(requestTo(URL)).andExpect(method(POST))
                .andExpect(jsonPath("$.origen.latitude").value(6.2502))
                .andExpect(jsonPath("$.destino.longitude").value(-75.5672))
                .andExpect(jsonPath("$.paradas.length()").value(1))
                .andExpect(jsonPath("$.paradas[0].latitude").value(6.23))
                .andExpect(jsonPath("$.vehicle_type").value("motorcycle"))
                .andExpect(jsonPath("$.route_type").value("fastest"))
                .andRespond(withSuccess(RESPUESTA, MediaType.APPLICATION_JSON));

        RouteResult r = client.route(ORIGEN, DESTINO, List.of(punto(6.23, -75.57)), TripRequestDTO.TipoVehiculo.MOTO);

        assertThat(r.durationSeconds()).isEqualTo(720);
        assertThat(r.distanceMeters()).isEqualTo(5400);
        assertThat(r.overviewPolyline()).isEqualTo("abc");
        assertThat(r.steps()).hasSize(1);
        assertThat(r.steps().get(0).getDistanciaMetros()).isEqualTo(500);
        assertThat(r.steps().get(0).getEndLng()).isEqualTo(-75.565);
        server.verify();
    }

    @Test
    @DisplayName("la alternativa es la primera con geometría distinta de la principal")
    void alternativaDistinta() {
        server.expect(requestTo(URL)).andRespond(withSuccess(RESPUESTA, MediaType.APPLICATION_JSON));

        RouteResult r = client.route(ORIGEN, DESTINO, List.of(), TripRequestDTO.TipoVehiculo.CARRO);

        assertThat(r.alternative()).isNotNull();
        assertThat(r.alternative().routeType()).isEqualTo("shortest");
        assertThat(r.alternative().overviewPolyline()).isEqualTo("xyz");
        assertThat(r.alternative().durationSeconds()).isEqualTo(760);
    }

    @Test
    @DisplayName("si el routing service calculó la ruta más seca, esa es la alternativa (spec 010)")
    void prefiereLaMasSeca() {
        server.expect(requestTo(URL)).andRespond(withSuccess("""
                {"distanciaMetros": 5400, "duracionSegundos": 720, "overviewPolyline": "abc", "pasos": [],
                 "alternativas": [{"distanciaMetros": 5100, "duracionSegundos": 760, "overviewPolyline": "xyz",
                                   "pasos": [], "route_type": "shortest"},
                                  {"distanciaMetros": 6200, "duracionSegundos": 840, "overviewPolyline": "seca",
                                   "pasos": [], "route_type": "dryest", "rain_exposure": 0.12}]}""",
                MediaType.APPLICATION_JSON));

        RouteResult r = client.route(ORIGEN, DESTINO, List.of(), TripRequestDTO.TipoVehiculo.CARRO);

        assertThat(r.alternative().routeType()).isEqualTo("dryest");
        assertThat(r.alternative().overviewPolyline()).isEqualTo("seca");
        assertThat(r.alternative().durationSeconds()).isEqualTo(840);
    }

    @Test
    @DisplayName("sin paradas no envía el campo y sin alternativas distintas devuelve null")
    void sinParadasNiAlternativa() {
        server.expect(requestTo(URL))
                .andExpect(jsonPath("$.paradas").doesNotExist())
                .andExpect(jsonPath("$.vehicle_type").value("bike"))
                .andRespond(withSuccess("""
                        {"distanciaMetros": 100, "duracionSegundos": 30, "overviewPolyline": "p", "pasos": []}""",
                        MediaType.APPLICATION_JSON));

        RouteResult r = client.route(ORIGEN, DESTINO, null, TripRequestDTO.TipoVehiculo.BICICLETA);

        assertThat(r.alternative()).isNull();
        assertThat(r.steps()).isEmpty();
    }

    @Test
    @DisplayName("mapeo de vehículos al contrato del routing service")
    void mapeoVehiculo() {
        assertThat(RoutingApiClient.vehicleType(null)).isEqualTo("car");
        assertThat(RoutingApiClient.vehicleType(TripRequestDTO.TipoVehiculo.CARRO)).isEqualTo("car");
        assertThat(RoutingApiClient.vehicleType(TripRequestDTO.TipoVehiculo.MOTO)).isEqualTo("motorcycle");
        assertThat(RoutingApiClient.vehicleType(TripRequestDTO.TipoVehiculo.BICICLETA)).isEqualTo("bike");
    }

    @Test
    @DisplayName("400 del routing service (sin ruta) → NoRouteException")
    void sinRuta() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.BAD_REQUEST)
                .contentType(MediaType.APPLICATION_JSON).body("{\"detail\": \"No route found\"}"));

        assertThatThrownBy(() -> client.route(ORIGEN, DESTINO, null, null))
                .isInstanceOf(NoRouteException.class);
    }

    @Test
    @DisplayName("500 o conexión rechazada → RoutingUnavailableException")
    void noDisponible() {
        server.expect(requestTo(URL)).andRespond(withStatus(HttpStatus.INTERNAL_SERVER_ERROR));
        assertThatThrownBy(() -> client.route(ORIGEN, DESTINO, null, null))
                .isInstanceOf(RoutingUnavailableException.class);

        server.reset();
        server.expect(requestTo(URL)).andRespond(request -> {
            throw new ResourceAccessException("Connection refused", new IOException("refused"));
        });
        assertThatThrownBy(() -> client.route(ORIGEN, DESTINO, null, null))
                .isInstanceOf(RoutingUnavailableException.class);
    }
}
