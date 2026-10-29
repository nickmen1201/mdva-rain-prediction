package ti.mdva.controller;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.ResponseEntity;
import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.model.dto.WeatherGridResultadoDTO;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.weather.HourlyInputs;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class WeatherControllerTest {

    /** Stub del WeatherMLService para evitar llamadas reales a Open-Meteo/ML en tests. */
    private static class StubWeatherService implements WeatherMLService {
        final AtomicInteger callsPredict = new AtomicInteger();
        final AtomicInteger callsForecast = new AtomicInteger();
        final AtomicInteger callsGrid = new AtomicInteger();
        double probFijo = 0.42;

        @Override
        public RainPredictionDTO predictRainForLocation(double lat, double lng) {
            callsPredict.incrementAndGet();
            return RainPredictionDTO.builder()
                    .llueve(probFijo >= 0.5)
                    .probabilidadRf(probFijo)
                    .probabilidadRl(probFijo)
                    .temperaturaC(20.0)
                    .humedadPct(80.0)
                    .build();
        }

        @Override
        public HourlyInputs currentInputs(double lat, double lng) {
            throw new UnsupportedOperationException("no se usa en estos tests");
        }

        @Override
        public List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas) {
            callsForecast.incrementAndGet();
            return List.of(
                HourlyForecastDTO.builder()
                    .timestamp(OffsetDateTime.now())
                    .hora(14)
                    .probabilidadRf(0.3)
                    .temperaturaC(22.0)
                    .build(),
                HourlyForecastDTO.builder()
                    .timestamp(OffsetDateTime.now().plusHours(1))
                    .hora(15)
                    .probabilidadRf(0.6)
                    .temperaturaC(21.0)
                    .build()
            );
        }

        @Override
        public WeatherGridResponseDTO predictGridForArea(List<WeatherGridPointDTO> puntos) {
            callsGrid.incrementAndGet();
            return new WeatherGridResponseDTO(
                puntos.stream()
                    .map(p -> new WeatherGridResultadoDTO(p.lat(), p.lng(), probFijo))
                    .toList(),
                Instant.now(),
                "TEST",
                180
            );
        }
    }

    private final StubWeatherService stub = new StubWeatherService();
    private final WeatherController controller = new WeatherController(stub);

    @Test
    @DisplayName("predict-grid: llama predictRainForLocation por cada punto y arma respuesta")
    void predictGridDevuelveResultadosPorPunto() {
        Map<String, List<Map<String, Double>>> body = Map.of(
            "puntos", List.of(
                Map.of("lat", 6.24, "lng", -75.58),
                Map.of("lat", 6.25, "lng", -75.59),
                Map.of("lat", 6.26, "lng", -75.60)
            )
        );

        ResponseEntity<WeatherGridResponseDTO> resp = controller.predictGrid(body);

        assertThat(resp.getStatusCode().is2xxSuccessful()).isTrue();
        List<WeatherGridResultadoDTO> resultados = resp.getBody().resultados();
        assertThat(resultados).hasSize(3);
        assertThat(resultados).allSatisfy(r -> {
            assertThat(r.probabilidadRf()).isEqualTo(0.42);
            assertThat(r.lat()).isBetween(6.0, 7.0);
            assertThat(r.lng()).isBetween(-76.0, -75.0);
        });
        assertThat(stub.callsGrid.get()).isEqualTo(1);
    }

    @Test
    @DisplayName("predict-grid: con lista vacía retorna lista vacía sin llamar al servicio")
    void predictGridConListaVacia() {
        Map<String, List<Map<String, Double>>> body = Map.of("puntos", List.of());

        ResponseEntity<WeatherGridResponseDTO> resp = controller.predictGrid(body);

        assertThat(resp.getBody().resultados()).isEmpty();
        assertThat(stub.callsPredict.get()).isZero();
        assertThat(stub.callsGrid.get()).isEqualTo(1);
    }

    @Test
    @DisplayName("predict-grid: un fallo del servicio se propaga; nunca se inventan probabilidades (spec 007, H-22)")
    void predictGridPropagaFallos() {
        WeatherMLService stubFalla = new WeatherMLService() {
            @Override public RainPredictionDTO predictRainForLocation(double lat, double lng) { return null; }
            @Override public HourlyInputs currentInputs(double lat, double lng) { return null; }
            @Override public List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas) { return List.of(); }
            @Override public WeatherGridResponseDTO predictGridForArea(List<WeatherGridPointDTO> puntos) {
                throw new IllegalStateException("Open-Meteo no respondió");
            }
        };
        WeatherController c = new WeatherController(stubFalla);

        Map<String, List<Map<String, Double>>> body = Map.of(
            "puntos", List.of(Map.of("lat", 6.24, "lng", -75.58))
        );

        assertThatThrownBy(() -> c.predictGrid(body)).isInstanceOf(IllegalStateException.class);
    }

    @Test
    @DisplayName("forecast: delega al servicio y devuelve lista de predicciones horarias")
    void forecastDelegaYDevuelveLista() {
        ResponseEntity<List<HourlyForecastDTO>> resp = controller.getHourlyForecast(6.24, -75.58, 6);

        assertThat(resp.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(resp.getBody()).hasSize(2);
        assertThat(resp.getBody()).extracting(HourlyForecastDTO::getHora).containsExactly(14, 15);
        assertThat(stub.callsForecast.get()).isEqualTo(1);
    }

    @Test
    @DisplayName("current (HU014): delega a predictRainForLocation y devuelve RainPredictionDTO")
    void currentDelegaYDevuelvePrediccion() {
        var resp = controller.getCurrent(6.24, -75.58);

        assertThat(resp.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().getProbabilidadRf()).isEqualTo(0.42);
        assertThat(stub.callsPredict.get()).isEqualTo(1);
    }

    @Test
    @DisplayName("best-window: usa forecast y devuelve recomendación válida")
    void bestWindowUsaForecastYDevuelveRecomendacion() {
        var resp = controller.getBestWindow(6.24, -75.58, 6);

        assertThat(resp.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(resp.getBody()).isNotNull();
        assertThat(resp.getBody().getMensaje()).isNotBlank();
        assertThat(resp.getBody().getSalirAhora()).isNotNull();
        assertThat(stub.callsForecast.get()).isEqualTo(1);
    }
}
