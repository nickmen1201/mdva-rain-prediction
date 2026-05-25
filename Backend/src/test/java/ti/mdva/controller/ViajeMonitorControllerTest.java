package ti.mdva.controller;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.service.impl.TripMonitorServiceImpl;

import java.time.OffsetDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Tests unitarios de ViajeMonitorController (HU031).
 * Verifica el contrato HTTP sin levantar Spring: stubs de servicio + repo.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ViajeMonitorController — endpoints de monitoreo activo")
class ViajeMonitorControllerTest {

    @Mock private TripMonitorServiceImpl tripMonitorService;
    @Mock private AlertaViajeRepository  alertaViajeRepository;

    private ViajeMonitorController controller;

    private static final int ID_VIAJE = 42;

    @BeforeEach
    void setup() {
        controller = new ViajeMonitorController(tripMonitorService, alertaViajeRepository);
    }

    @Test
    @DisplayName("POST /posicion delega en el service y devuelve MonitoreoResponseDTO")
    void reportarPosicionDelegaAlService() {
        MonitoreoResponseDTO esperado = MonitoreoResponseDTO.builder()
                .condicionesActuales(RainPredictionDTO.builder().probabilidadRf(0.3).build())
                .build();
        when(tripMonitorService.evaluarPosicion(ID_VIAJE, 6.24, -75.58)).thenReturn(esperado);

        ResponseEntity<MonitoreoResponseDTO> r = controller.reportarPosicion(
                ID_VIAJE, new ViajeMonitorController.PosicionRequest(6.24, -75.58));

        assertThat(r.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(r.getBody()).isSameAs(esperado);
        verify(tripMonitorService).evaluarPosicion(ID_VIAJE, 6.24, -75.58);
    }

    @Test
    @DisplayName("GET /alertas sin filtro devuelve todas las alertas")
    void obtenerAlertasSinFiltroDevuelveTodas() {
        when(alertaViajeRepository.findByViajeId(ID_VIAJE)).thenReturn(List.of(
                alerta(1, false), alerta(2, true), alerta(3, false)
        ));

        ResponseEntity<List<AlertaViajeDTO>> r = controller.obtenerAlertas(ID_VIAJE, false);

        assertThat(r.getBody()).hasSize(3);
    }

    @Test
    @DisplayName("GET /alertas?soloNoLeidas=true filtra leida=true")
    void obtenerAlertasFiltraLeidas() {
        when(alertaViajeRepository.findByViajeId(ID_VIAJE)).thenReturn(List.of(
                alerta(1, false), alerta(2, true), alerta(3, false)
        ));

        ResponseEntity<List<AlertaViajeDTO>> r = controller.obtenerAlertas(ID_VIAJE, true);

        assertThat(r.getBody()).hasSize(2);
        assertThat(r.getBody()).extracting(AlertaViajeDTO::getIdAlerta).containsExactly(1, 3);
    }

    @Test
    @DisplayName("PATCH /alertas/{idAlerta}/leer marca la alerta como leída y devuelve 200")
    void marcarLeidaActualizaRepo() {
        ResponseEntity<Void> r = controller.marcarLeida(ID_VIAJE, 99);

        assertThat(r.getStatusCode().is2xxSuccessful()).isTrue();
        verify(alertaViajeRepository).marcarComoLeida(99);
        verifyNoMoreInteractions(alertaViajeRepository);
    }

    private AlertaViajeDTO alerta(int id, boolean leida) {
        return AlertaViajeDTO.builder()
                .idAlerta(id)
                .leida(leida)
                .mensaje("test")
                .nivelSeveridad("INFORMATIVA")
                .timestampGeneracion(OffsetDateTime.now())
                .build();
    }
}
