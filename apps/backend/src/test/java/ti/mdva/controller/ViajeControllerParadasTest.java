package ti.mdva.controller;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import ti.mdva.jooq.tables.pojos.Usuarios;
import ti.mdva.model.dto.AlertaActualDTO;
import ti.mdva.model.dto.ParadaDTO;
import ti.mdva.model.dto.TripResponseDTO.AlertaNivel;
import ti.mdva.repositories.UsuarioRepositoryImpl;
import ti.mdva.usecases.ViajeUseCase;

import java.security.Principal;
import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * Tests unitarios de ViajeController para endpoints HU031 (alerta-actual) y HU032 (paradas).
 * Foca en autorización (401 sin Principal) y en delegación correcta al UseCase.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("ViajeController — endpoints de paradas (HU032) y alerta-actual (HU031)")
class ViajeControllerParadasTest {

    @Mock private ViajeUseCase           viajeUseCase;
    @Mock private UsuarioRepositoryImpl  usuarioRepository;

    private ViajeController controller;

    private static final int ID_VIAJE   = 42;
    private static final int ID_USUARIO = 7;
    private static final String USERNAME = "jhosep";

    @BeforeEach
    void setup() {
        controller = new ViajeController(viajeUseCase, usuarioRepository);
    }

    private Principal principalDe(String username) {
        return () -> username;
    }

    private Usuarios usuarioFake() {
        Usuarios u = new Usuarios();
        u.setId((long) ID_USUARIO);
        u.setUsername(USERNAME);
        return u;
    }

    // ── /paradas ───────────────────────────────────────────────────────────────

    @Test
    @DisplayName("GET /paradas sin Principal devuelve 401")
    void listarParadasSinPrincipal401() {
        ResponseEntity<List<ParadaDTO>> r = controller.listarParadas(ID_VIAJE, null);

        assertThat(r.getStatusCode().value()).isEqualTo(401);
        verifyNoInteractions(viajeUseCase, usuarioRepository);
    }

    @Test
    @DisplayName("GET /paradas con usuario válido delega al UseCase y devuelve la lista")
    void listarParadasDevuelveLista() {
        when(usuarioRepository.findByUsername(USERNAME)).thenReturn(Optional.of(usuarioFake()));
        List<ParadaDTO> paradas = List.of(
            ParadaDTO.builder().idParada(1).orden(1).lat(6.20).lng(-75.58).nombre("UPB").finalizado(false).build(),
            ParadaDTO.builder().idParada(2).orden(2).lat(6.25).lng(-75.57).nombre("Centro").finalizado(true).build()
        );
        when(viajeUseCase.obtenerParadas(ID_VIAJE, ID_USUARIO)).thenReturn(paradas);

        ResponseEntity<List<ParadaDTO>> r = controller.listarParadas(ID_VIAJE, principalDe(USERNAME));

        assertThat(r.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(r.getBody()).hasSize(2);
        assertThat(r.getBody()).extracting(ParadaDTO::getOrden).containsExactly(1, 2);
    }

    @Test
    @DisplayName("PATCH /paradas/{orden}/finalizar sin Principal devuelve 401")
    void finalizarParadaSinPrincipal401() {
        ResponseEntity<Void> r = controller.finalizarParada(ID_VIAJE, 1, null);

        assertThat(r.getStatusCode().value()).isEqualTo(401);
        verifyNoInteractions(viajeUseCase);
    }

    @Test
    @DisplayName("PATCH /paradas/{orden}/finalizar delega al UseCase y devuelve 200")
    void finalizarParadaDelegaAlUseCase() {
        when(usuarioRepository.findByUsername(USERNAME)).thenReturn(Optional.of(usuarioFake()));

        ResponseEntity<Void> r = controller.finalizarParada(ID_VIAJE, 2, principalDe(USERNAME));

        assertThat(r.getStatusCode().is2xxSuccessful()).isTrue();
        verify(viajeUseCase).finalizarParada(ID_VIAJE, 2, ID_USUARIO);
    }

    // ── /alerta-actual (HU031) ─────────────────────────────────────────────────

    @Test
    @DisplayName("GET /alerta-actual sin Principal devuelve 401")
    void alertaActualSinPrincipal401() {
        ResponseEntity<AlertaActualDTO> r = controller.alertaActual(ID_VIAJE, null);

        assertThat(r.getStatusCode().value()).isEqualTo(401);
        verifyNoInteractions(viajeUseCase);
    }

    @Test
    @DisplayName("GET /alerta-actual delega y devuelve AlertaActualDTO")
    void alertaActualDelegaAlUseCase() {
        when(usuarioRepository.findByUsername(USERNAME)).thenReturn(Optional.of(usuarioFake()));
        AlertaActualDTO esperado = AlertaActualDTO.builder()
                .idViaje(ID_VIAJE)
                .calculadoEn(OffsetDateTime.now())
                .alertaNivel(AlertaNivel.AMARILLO)
                .factorAjuste(1.20)
                .sugerirRutaAlterna(false)
                .build();
        when(viajeUseCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO)).thenReturn(esperado);

        ResponseEntity<AlertaActualDTO> r = controller.alertaActual(ID_VIAJE, principalDe(USERNAME));

        assertThat(r.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(r.getBody()).isSameAs(esperado);
        assertThat(r.getBody().getAlertaNivel()).isEqualTo(AlertaNivel.AMARILLO);
    }
}
