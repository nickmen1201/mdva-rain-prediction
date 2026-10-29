package ti.mdva.service.impl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.service.weather.HourlyInputs;
import ti.mdva.service.weather.MlApiV2Client;
import ti.mdva.service.weather.OpenMeteoForecastClient;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.stream.IntStream;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.Mockito.*;

/**
 * Tests de WeatherMLServiceImpl (specs/007-backend-weather-openmeteo): Open-Meteo y el ML API v2
 * se sustituyen por mocks y el reloj se fija en 2026-10-29T15:20Z (10:20 en Bogotá).
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("WeatherMLServiceImpl — clima de Open-Meteo y modelo v2")
class WeatherMLServiceImplTest {

    private static final Instant AHORA = Instant.parse("2026-10-29T15:20:00Z");
    private static final double LAT = 6.2442;
    private static final double LNG = -75.5812;

    @Mock private OpenMeteoForecastClient openMeteo;
    @Mock private MlApiV2Client mlApi;

    private WeatherMLServiceImpl service;

    @BeforeEach
    void setup() {
        service = new WeatherMLServiceImpl(openMeteo, mlApi, Clock.fixed(AHORA, ZoneOffset.UTC));
    }

    /** Serie horaria desde 00:00 UTC del día; la temperatura es la hora UTC para identificar cada fila. */
    private static List<HourlyInputs> serie(int horas) {
        Instant inicio = AHORA.truncatedTo(ChronoUnit.DAYS);
        return IntStream.range(0, horas)
                .mapToObj(h -> new HourlyInputs(inicio.plus(h, ChronoUnit.HOURS),
                        h, 80.0, 15.0, 90.0, 2.0, 180.0, 1013.0, 0.0, 100.0))
                .toList();
    }

    private static List<MlApiV2Client.Prediction> preds(List<HourlyInputs> entradas, double p) {
        return entradas.stream().map(e -> new MlApiV2Client.Prediction(p, "AMARILLO")).toList();
    }

    @Test
    @DisplayName("Clima actual: usa la hora UTC en curso, informa su instante y no inventa la probabilidad RL")
    void climaActual() {
        when(openMeteo.hourly(LAT, LNG)).thenReturn(serie(48));
        when(mlApi.predictBatch(anyList())).thenReturn(List.of(new MlApiV2Client.Prediction(0.64, "AMARILLO")));

        RainPredictionDTO r = service.predictRainForLocation(LAT, LNG);

        verify(mlApi).predictBatch(argThat(l -> l.size() == 1
                && l.get(0).timeUtc().equals(Instant.parse("2026-10-29T15:00:00Z"))));
        assertThat(r.getProbabilidadRf()).isEqualTo(0.64);
        assertThat(r.getProbabilidadRl()).isNull();
        assertThat(r.getLlueve()).isTrue();
        assertThat(r.getTemperaturaC()).isEqualTo(15.0);
        assertThat(r.getTimestampDatoUtc().toInstant()).isEqualTo(Instant.parse("2026-10-29T15:00:00Z"));
    }

    @Test
    @DisplayName("Dos consultas del mismo punto dentro de 3 minutos: una sola llamada a cada fuente")
    void cacheDePrediccion() {
        when(openMeteo.hourly(LAT, LNG)).thenReturn(serie(48));
        when(mlApi.predictBatch(anyList())).thenReturn(List.of(new MlApiV2Client.Prediction(0.2, "VERDE")));

        service.predictRainForLocation(LAT, LNG);
        service.predictRainForLocation(LAT, LNG);

        verify(openMeteo, times(1)).hourly(LAT, LNG);
        verify(mlApi, times(1)).predictBatch(anyList());
    }

    @Test
    @DisplayName("Pronóstico: 6 horas consecutivas desde la hora en curso, con hora local de Bogotá")
    void pronosticoHorario() {
        when(openMeteo.hourly(LAT, LNG)).thenReturn(serie(48));
        when(mlApi.predictBatch(anyList())).thenAnswer(inv -> preds(inv.getArgument(0), 0.3));

        List<HourlyForecastDTO> f = service.getHourlyForecast(LAT, LNG, 6);

        assertThat(f).hasSize(6);
        assertThat(f).extracting(HourlyForecastDTO::getHora).containsExactly(10, 11, 12, 13, 14, 15);
        assertThat(f.get(0).getTimestamp().toInstant()).isEqualTo(Instant.parse("2026-10-29T15:00:00Z"));
        assertThat(f).extracting(HourlyForecastDTO::getProbabilidadRf).containsOnly(0.3);
        verify(mlApi, times(1)).predictBatch(anyList());
    }

    @Test
    @DisplayName("Heatmap de 81 puntos: exactamente 1 llamada de clima y 1 de predicción")
    void heatmapUnaLlamadaPorFuente() {
        List<WeatherGridPointDTO> puntos = IntStream.range(0, 81)
                .mapToObj(i -> new WeatherGridPointDTO(6.10 + (i / 9) * 0.03, -75.70 + (i % 9) * 0.03))
                .toList();
        when(openMeteo.hourly(anyList())).thenAnswer(inv ->
                ((List<?>) inv.getArgument(0)).stream().map(p -> serie(48)).toList());
        when(mlApi.predictBatch(anyList())).thenAnswer(inv -> preds(inv.getArgument(0), 0.7));

        WeatherGridResponseDTO r = service.predictGridForArea(puntos);

        verify(openMeteo, times(1)).hourly(anyList());
        verify(mlApi, times(1)).predictBatch(argThat(l -> l.size() == 81));
        verify(openMeteo, never()).hourly(anyDouble(), anyDouble());
        assertThat(r.resultados()).hasSize(81);
        assertThat(r.source()).isEqualTo("OPEN_METEO_ML_V2");
    }

    @Test
    @DisplayName("Heatmap con la fuente de clima caída: error explícito, nunca probabilidades en 0")
    void heatmapFallaExplicitamente() {
        when(openMeteo.hourly(anyList())).thenThrow(new IllegalStateException("Open-Meteo no respondió"));

        assertThatThrownBy(() -> service.predictGridForArea(List.of(new WeatherGridPointDTO(6.24, -75.58))))
                .isInstanceOf(IllegalStateException.class);
        verifyNoInteractions(mlApi);
    }

    @Test
    @DisplayName("Heatmap con más de 81 puntos: rechazado")
    void heatmapDemasiadosPuntos() {
        List<WeatherGridPointDTO> puntos = IntStream.range(0, 82).mapToObj(i -> new WeatherGridPointDTO(6.2, -75.5)).toList();

        assertThatThrownBy(() -> service.predictGridForArea(puntos)).isInstanceOf(IllegalArgumentException.class);
        verifyNoInteractions(openMeteo, mlApi);
    }

    @Test
    @DisplayName("Sin la hora en curso en la serie: se usa la siguiente disponible")
    void horaSiguienteDisponible() {
        List<HourlyInputs> sinLaHora = serie(48).stream()
                .filter(h -> !h.timeUtc().equals(Instant.parse("2026-10-29T15:00:00Z")))
                .toList();
        when(openMeteo.hourly(LAT, LNG)).thenReturn(sinLaHora);

        assertThat(service.currentInputs(LAT, LNG).timeUtc()).isEqualTo(Instant.parse("2026-10-29T16:00:00Z"));
        verify(mlApi, never()).predictBatch(any());
    }
}
