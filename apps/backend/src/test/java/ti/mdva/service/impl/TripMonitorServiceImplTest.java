package ti.mdva.service.impl;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.repositories.CondicionesSnapshotRepository;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.weather.HourlyInputs;
import ti.mdva.service.weather.MlApiV2Client;

import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Tests del orquestador del monitoreo activo (HU031, specs/007-backend-weather-openmeteo).
 *
 * Las reglas RF-17 viven en el ML API (/v2/monitor/trip); aquí el cliente se sustituye por un mock.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("TripMonitorServiceImpl — orquestación del monitoreo (HU031)")
class TripMonitorServiceImplTest {

    @Mock private CondicionesSnapshotRepository snapshotRepo;
    @Mock private AlertaViajeRepository         alertaRepo;
    @Mock private WeatherMLService              weatherMLService;
    @Mock private MlApiV2Client                 mlApi;

    private TripMonitorServiceImpl service;

    private static final int    ID_VIAJE = 42;
    private static final double LAT      = 6.2442;
    private static final double LNG      = -75.5812;
    private static final OffsetDateTime INSTANTE_DATO = OffsetDateTime.of(2026, 10, 29, 14, 0, 0, 0, ZoneOffset.UTC);
    private static final HourlyInputs ACTUAL = new HourlyInputs(
            Instant.parse("2026-10-29T15:00:00Z"), 20.0, 75.0, 15.5, 60.0, 2.0, 180.0, 1013.0, 0.0, 120.0);

    @BeforeEach
    void setup() {
        service = new TripMonitorServiceImpl(snapshotRepo, alertaRepo, weatherMLService, mlApi);
    }

    @Test
    @DisplayName("Snapshot ausente: devuelve solo condiciones actuales sin tocar ML ni persistir alerta")
    void snapshotAusenteSoloDevuelveCondicionesActuales() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.empty());
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.3));

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva()).isNull();
        assertThat(r.getCondicionesActuales()).isNotNull();
        assertThat(r.getCondicionesActuales().getProbabilidadRf()).isEqualTo(0.3);
        verifyNoInteractions(mlApi);
        verifyNoInteractions(alertaRepo);
    }

    @Test
    @DisplayName("Nivel ESTABLE sin latencia: no genera alerta y no persiste nada")
    void nivelEstableSinLatenciaNoGeneraAlerta() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.3));
        when(weatherMLService.currentInputs(LAT, LNG)).thenReturn(ACTUAL);
        when(mlApi.monitorTrip(0.3, INSTANTE_DATO, ACTUAL))
                .thenReturn(resultado("ESTABLE", 0.32));

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva()).isNull();
        verify(alertaRepo, never()).save(any(), anyInt(), anyDouble(), anyDouble(), anyDouble(), anyBoolean());
    }

    @Test
    @DisplayName("Nivel SIGNIFICATIVO prob<0.6: alerta PELIGRO/NUEVA_RUTA persistida con id generado")
    void nivelSignificativoGeneraAlertaPersistida() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.5));
        when(weatherMLService.currentInputs(LAT, LNG)).thenReturn(ACTUAL);
        when(mlApi.monitorTrip(0.3, INSTANTE_DATO, ACTUAL))
                .thenReturn(resultado("SIGNIFICATIVO", 0.55));
        when(alertaRepo.save(any(), anyInt(), anyDouble(), anyDouble(), anyDouble(), anyBoolean())).thenReturn(99);

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva()).isNotNull();
        assertThat(r.getAlertaNueva().getNivelSeveridad()).isEqualTo("PELIGRO");
        assertThat(r.getAlertaNueva().getAccionSugerida()).isEqualTo("NUEVA_RUTA");
        assertThat(r.getAlertaNueva().getMensaje()).isEqualTo("Nueva ruta a considerar");
        assertThat(r.getAlertaNueva().getIdAlerta()).isEqualTo(99);
        verify(alertaRepo).save(any(), eq(ID_VIAJE), eq(LAT), eq(LNG), eq(0.55), eq(false));
    }

    @Test
    @DisplayName("Nivel CRITICO: alerta CRISIS con mensaje literal de cancelación")
    void nivelCriticoGeneraCrisis() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.9));
        when(weatherMLService.currentInputs(LAT, LNG)).thenReturn(ACTUAL);
        when(mlApi.monitorTrip(0.3, INSTANTE_DATO, ACTUAL))
                .thenReturn(resultado("CRITICO", 0.92));
        when(alertaRepo.save(any(), anyInt(), anyDouble(), anyDouble(), anyDouble(), anyBoolean())).thenReturn(100);

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva().getNivelSeveridad()).isEqualTo("CRISIS");
        assertThat(r.getAlertaNueva().getAccionSugerida()).isEqualTo("CANCELAR_VIAJE");
        assertThat(r.getAlertaNueva().getMensaje()).isEqualTo("SE RECOMIENDA CANCELAR VIAJE");
    }

    @Test
    @DisplayName("El ML API rechaza la petición: error explícito, sin alerta inventada ni persistida")
    void rechazoDelMlApiSePropaga() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.4));
        when(weatherMLService.currentInputs(LAT, LNG)).thenReturn(ACTUAL);
        when(mlApi.monitorTrip(anyDouble(), any(), any()))
                .thenThrow(new IllegalStateException("El ML API rechazó la petición a /v2/monitor/trip (422)"));

        assertThatThrownBy(() -> service.evaluarPosicion(ID_VIAJE, LAT, LNG))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("422");
        verifyNoInteractions(alertaRepo);
    }

    @Test
    @DisplayName("Usa el instante real del dato del snapshot, no el del snapshot ni \"ahora\"")
    void usaElInstanteDelDatoDelSnapshot() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.3));
        when(weatherMLService.currentInputs(LAT, LNG)).thenReturn(ACTUAL);
        when(mlApi.monitorTrip(anyDouble(), any(), any())).thenReturn(resultado("ESTABLE", 0.3));

        service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        verify(mlApi).monitorTrip(0.3, INSTANTE_DATO, ACTUAL);
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private RainPredictionDTO condicionesActuales(double prob) {
        return RainPredictionDTO.builder()
                .probabilidadRf(prob)
                .llueve(prob >= 0.5)
                .temperaturaC(20.0)
                .humedadPct(75.0)
                .coberturaAnubosaPct(60.0)
                .velocidadVientoMs(2.0)
                .build();
    }

    private CondicionesSnapshotRepository.SnapshotData snapshotBase() {
        return new CondicionesSnapshotRepository.SnapshotData(
                0.3,
                20.0,
                INSTANTE_DATO.plusMinutes(20), // timestamp del snapshot (al planificar)
                INSTANTE_DATO                  // instante del dato meteorológico
        );
    }

    private static MlApiV2Client.MonitorResult resultado(String nivel, double prob) {
        return new MlApiV2Client.MonitorResult(prob, prob - 0.3, 60, false, nivel);
    }
}
