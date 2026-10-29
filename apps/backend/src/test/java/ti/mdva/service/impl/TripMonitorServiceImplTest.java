package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.repositories.CondicionesSnapshotRepository;
import ti.mdva.service.WeatherMLService;

import java.time.OffsetDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Tests del orquestador del monitoreo activo (Sprint 5.2A / HU031).
 *
 * El RestTemplate interno se sustituye via ReflectionTestUtils para no tocar la red.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("TripMonitorServiceImpl — orquestación del monitoreo (HU031)")
class TripMonitorServiceImplTest {

    @Mock private CondicionesSnapshotRepository snapshotRepo;
    @Mock private AlertaViajeRepository         alertaRepo;
    @Mock private WeatherMLService              weatherMLService;
    @Mock private RestTemplate                  restTemplate;

    private TripMonitorServiceImpl service;

    private static final int    ID_VIAJE = 42;
    private static final double LAT      = 6.2442;
    private static final double LNG      = -75.5812;
    private static final String ML_URL   = "http://ml:8081";

    @BeforeEach
    void setup() {
        service = new TripMonitorServiceImpl(snapshotRepo, alertaRepo, weatherMLService, ML_URL);
        ReflectionTestUtils.setField(service, "restTemplate", restTemplate);
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
        verifyNoInteractions(restTemplate);
        verifyNoInteractions(alertaRepo);
    }

    @Test
    @DisplayName("Nivel ESTABLE sin latencia: no genera alerta y no persiste nada")
    void nivelEstableSinLatenciaNoGeneraAlerta() throws Exception {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.3));
        when(restTemplate.postForEntity(anyString(), any(), eq(JsonNode.class)))
                .thenReturn(jsonResp("{\"nivel_cambio\":\"ESTABLE\",\"probabilidad_rf_actual\":0.32,\"dato_con_latencia\":false}"));

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva()).isNull();
        verify(alertaRepo, never()).save(any(), anyInt(), anyDouble(), anyDouble(), anyDouble(), anyBoolean());
    }

    @Test
    @DisplayName("Nivel SIGNIFICATIVO prob<0.6: alerta PELIGRO/NUEVA_RUTA persistida con id generado")
    void nivelSignificativoGeneraAlertaPersistida() throws Exception {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.5));
        when(restTemplate.postForEntity(anyString(), any(), eq(JsonNode.class)))
                .thenReturn(jsonResp("{\"nivel_cambio\":\"SIGNIFICATIVO\",\"probabilidad_rf_actual\":0.55,\"dato_con_latencia\":false}"));
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
    void nivelCriticoGeneraCrisis() throws Exception {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.9));
        when(restTemplate.postForEntity(anyString(), any(), eq(JsonNode.class)))
                .thenReturn(jsonResp("{\"nivel_cambio\":\"CRITICO\",\"probabilidad_rf_actual\":0.92,\"dato_con_latencia\":false}"));
        when(alertaRepo.save(any(), anyInt(), anyDouble(), anyDouble(), anyDouble(), anyBoolean())).thenReturn(100);

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva().getNivelSeveridad()).isEqualTo("CRISIS");
        assertThat(r.getAlertaNueva().getAccionSugerida()).isEqualTo("CANCELAR_VIAJE");
        assertThat(r.getAlertaNueva().getMensaje()).isEqualTo("SE RECOMIENDA CANCELAR VIAJE");
    }

    @Test
    @DisplayName("ML responde body null: retorna condiciones actuales, sin alerta, sin persistir")
    void mlBodyNullNoGeneraAlerta() {
        when(snapshotRepo.findByViajeId(ID_VIAJE)).thenReturn(Optional.of(snapshotBase()));
        when(weatherMLService.predictRainForLocation(LAT, LNG)).thenReturn(condicionesActuales(0.4));
        when(restTemplate.postForEntity(anyString(), any(), eq(JsonNode.class)))
                .thenReturn(new ResponseEntity<>(null, HttpStatus.OK));

        MonitoreoResponseDTO r = service.evaluarPosicion(ID_VIAJE, LAT, LNG);

        assertThat(r.getAlertaNueva()).isNull();
        assertThat(r.getCondicionesActuales()).isNotNull();
        verifyNoInteractions(alertaRepo);
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private RainPredictionDTO condicionesActuales(double prob) {
        return RainPredictionDTO.builder()
                .probabilidadRf(prob)
                .probabilidadRl(prob)
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
                OffsetDateTime.now(),
                OffsetDateTime.now()
        );
    }

    private ResponseEntity<JsonNode> jsonResp(String json) throws Exception {
        return new ResponseEntity<>(new ObjectMapper().readTree(json), HttpStatus.OK);
    }
}
