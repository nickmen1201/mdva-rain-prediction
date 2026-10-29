package ti.mdva.usecases;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.AlertaActualDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.TripResponseDTO.AlertaNivel;
import ti.mdva.repositories.ViajeRepositoryImpl;
import ti.mdva.repositories.VehiculoRepositoryImpl;
import ti.mdva.service.GoogleMapsService;
import ti.mdva.service.WeatherMLService;

import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@DisplayName("ViajeUseCase.obtenerAlertaActual (HU031)")
class ViajeUseCaseAlertaActualTest {

    @Mock private ViajeRepositoryImpl viajeRepository;
    @Mock private VehiculoRepositoryImpl vehiculoRepository;
    @Mock private GoogleMapsService googleMapsService;
    @Mock private WeatherMLService weatherMLService;

    @InjectMocks private ViajeUseCase useCase;

    private static final Integer ID_VIAJE   = 42;
    private static final Integer ID_USUARIO = 7;

    private Viajes viajeBase;

    @BeforeEach
    void setup() {
        viajeBase = new Viajes();
        viajeBase.setIdViaje(ID_VIAJE);
        viajeBase.setIdUsuario(ID_USUARIO);
        viajeBase.setLatOrigen(6.2442);
        viajeBase.setLngOrigen(-75.5812);
        viajeBase.setDistanciaMetros(8_000);
    }

    private RainPredictionDTO predicConProbRf(double prob) {
        return RainPredictionDTO.builder()
                .probabilidadRf(prob)
                .probabilidadRl(prob)
                .llueve(prob > 0.5)
                .temperaturaC(20.0)
                .humedadPct(70.0)
                .coberturaAnubosaPct(50.0)
                .velocidadVientoMs(2.0)
                .build();
    }

    @Test
    @DisplayName("Lanza cuando el viaje no existe")
    void viajeInexistenteLanza() {
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining(String.valueOf(ID_VIAJE));
    }

    @Test
    @DisplayName("Lanza cuando el viaje pertenece a otro usuario (no filtra info)")
    void viajeDeOtroUsuarioLanza() {
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));

        Integer otroUsuario = ID_USUARIO + 1;
        assertThatThrownBy(() -> useCase.obtenerAlertaActual(ID_VIAJE, otroUsuario))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining(String.valueOf(ID_VIAJE));
        // El mensaje es idéntico al "no existe" para no revelar IDs ajenos
    }

    @Test
    @DisplayName("Lanza cuando el viaje no tiene coordenadas (caso legado pre-V2)")
    void viajeSinCoordenadasLanza() {
        viajeBase.setLatOrigen(null);
        viajeBase.setLngOrigen(null);
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));

        assertThatThrownBy(() -> useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("coordenadas");
    }

    @Test
    @DisplayName("Probabilidad baja → alerta VERDE, factor 1.0, sin sugerencia")
    void probabilidadBajaProduceVerde() {
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble()))
                .thenReturn(predicConProbRf(0.10));

        AlertaActualDTO r = useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO);

        assertThat(r.getIdViaje()).isEqualTo(ID_VIAJE);
        assertThat(r.getCalculadoEn()).isNotNull();
        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.VERDE);
        assertThat(r.getFactorAjuste()).isEqualTo(1.0);
        assertThat(r.getSugerirRutaAlterna()).isFalse();
        assertThat(r.getPrediccionLluvia()).isNotNull();
    }

    @Test
    @DisplayName("Probabilidad media → alerta AMARILLO, factor 1.20")
    void probabilidadMediaProduceAmarillo() {
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble()))
                .thenReturn(predicConProbRf(0.55));

        AlertaActualDTO r = useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO);

        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.AMARILLO);
        assertThat(r.getFactorAjuste()).isEqualTo(1.20);
        assertThat(r.getSugerirRutaAlterna()).isFalse();
    }

    @Test
    @DisplayName("Probabilidad alta + ruta >5km → ROJO + sugerir alterna")
    void probabilidadAltaConRutaLargaProduceRojoConAlterna() {
        viajeBase.setDistanciaMetros(8_000);
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble()))
                .thenReturn(predicConProbRf(0.85));

        AlertaActualDTO r = useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO);

        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.ROJO);
        assertThat(r.getFactorAjuste()).isEqualTo(1.35);
        assertThat(r.getSugerirRutaAlterna()).isTrue();
        assertThat(r.getRazonRutaAlterna()).isNotBlank();
    }

    @Test
    @DisplayName("Probabilidad alta + ruta ≤5km → ROJO sin sugerir alterna")
    void probabilidadAltaConRutaCortaNoSugiereAlterna() {
        viajeBase.setDistanciaMetros(3_000);
        when(viajeRepository.findById(ID_VIAJE)).thenReturn(Optional.of(viajeBase));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble()))
                .thenReturn(predicConProbRf(0.85));

        AlertaActualDTO r = useCase.obtenerAlertaActual(ID_VIAJE, ID_USUARIO);

        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.ROJO);
        assertThat(r.getSugerirRutaAlterna()).isFalse();
    }
}
