package ti.mdva.usecases;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.TripRequestDTO;
import ti.mdva.model.dto.TripResponseDTO;
import ti.mdva.model.dto.TripResponseDTO.AlertaNivel;
import ti.mdva.repositories.CondicionesSnapshotRepository;
import ti.mdva.repositories.ParadaViajeRepository;
import ti.mdva.repositories.VehiculoRepositoryImpl;
import ti.mdva.repositories.ViajeRepositoryImpl;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.routing.NoRouteException;
import ti.mdva.service.routing.RouteResult;
import ti.mdva.service.routing.RoutingApiClient;
import ti.mdva.service.routing.RoutingUnavailableException;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
@DisplayName("ViajeUseCase.planificarViaje — rutas propias, sin Google (spec 008)")
class ViajeUseCasePlanificarTest {

    @Mock private ViajeRepositoryImpl viajeRepository;
    @Mock private VehiculoRepositoryImpl vehiculoRepository;
    @Mock private RoutingApiClient routingApiClient;
    @Mock private WeatherMLService weatherMLService;
    @Mock private CondicionesSnapshotRepository snapshotRepo;
    @Mock private ParadaViajeRepository paradaRepo;

    @InjectMocks private ViajeUseCase useCase;

    private static final LocationPointDTO ORIGEN = punto("Parque Berrío", 6.2502, -75.5684);
    private static final LocationPointDTO DESTINO = punto("El Poblado", 6.2088, -75.5672);

    private static LocationPointDTO punto(String nombre, double lat, double lng) {
        return LocationPointDTO.builder().displayName(nombre).lat(lat).lng(lng).build();
    }

    private static RainPredictionDTO prob(double p) {
        return RainPredictionDTO.builder().probabilidadRf(p).llueve(p >= 0.5)
                .temperaturaC(20.0).humedadPct(70.0).coberturaAnubosaPct(50.0).velocidadVientoMs(2.0).build();
    }

    private static RouteResult ruta(int segundos, int metros, RouteResult.Alternative alt) {
        return new RouteResult(segundos, metros, "poly", List.of(), alt);
    }

    @BeforeEach
    void setup() {
        when(viajeRepository.save(any(Viajes.class))).thenAnswer(inv -> {
            Viajes v = inv.getArgument(0);
            v.setIdViaje(99);
            return v;
        });
        when(paradaRepo.findByViajeId(99)).thenReturn(List.of());
    }

    private TripRequestDTO request(List<LocationPointDTO> paradas, TripRequestDTO.ModoParadas modo,
                                   TripRequestDTO.TipoVehiculo tipo) {
        return TripRequestDTO.builder().origen(ORIGEN).destino(DESTINO).paradas(paradas)
                .modoParadas(modo).tipoVehiculo(tipo).build();
    }

    @Test
    @DisplayName("ROJO: tiempo base del routing service × 1.35, una sola vez; alerta del modelo v2")
    void ajusteUnicoPorLluvia() {
        when(routingApiClient.route(eq(ORIGEN), eq(DESTINO), anyList(), eq(TripRequestDTO.TipoVehiculo.CARRO)))
                .thenReturn(ruta(1200, 8000, null));
        when(weatherMLService.predictRainForLocation(6.2502, -75.5684)).thenReturn(prob(0.82));

        TripResponseDTO r = useCase.planificarViaje(7, request(null, null, null));

        assertThat(r.getTiempoBaseMin()).isEqualTo(20);
        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.ROJO);
        assertThat(r.getTiempoEstimadoMin()).isEqualTo((int) Math.ceil(20 * 1.35));
        assertThat(r.getDistanciaMetros()).isEqualTo(8000);
        assertThat(r.getOverviewPolyline()).isEqualTo("poly");
        assertThat(r.getIdViaje()).isEqualTo(99);
        verify(snapshotRepo).save(eq(99), eq(0.82), anyDouble(), anyDouble(), anyDouble(), anyDouble(), anyDouble(),
                eq("ROJO"), any());
    }

    @Test
    @DisplayName("VERDE: sin ajuste; la alternativa del routing service queda disponible")
    void alternativaDisponible() {
        when(routingApiClient.route(any(), any(), anyList(), any()))
                .thenReturn(ruta(600, 4000, new RouteResult.Alternative("shortest", 660, 3800, "alt")));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble())).thenReturn(prob(0.10));

        TripResponseDTO r = useCase.planificarViaje(7, request(null, null, null));

        assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.VERDE);
        assertThat(r.getTiempoEstimadoMin()).isEqualTo(10);
        assertThat(r.getRutaAlternaPolyline()).isEqualTo("alt");
        assertThat(r.getRutaAlternaTiempoMin()).isEqualTo(11);
        assertThat(r.getRutaAlternaTipo()).isEqualTo("shortest");
    }

    @Test
    @DisplayName("moto: el routing service recibe el tipo y el tiempo base tiene −15 % (regla del equipo)")
    void moto() {
        when(routingApiClient.route(any(), any(), anyList(), eq(TripRequestDTO.TipoVehiculo.MOTO)))
                .thenReturn(ruta(1200, 8000, null));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble())).thenReturn(prob(0.1));

        TripResponseDTO r = useCase.planificarViaje(7, request(null, null, TripRequestDTO.TipoVehiculo.MOTO));

        assertThat(r.getTiempoBaseMin()).isEqualTo(17);
    }

    @Test
    @DisplayName("OPTIMIZAR_RUTA: las paradas llegan al routing service y se guardan en orden óptimo")
    void paradasOptimizadas() {
        LocationPointDTO cerca = punto("cerca", 6.24, -75.568);
        LocationPointDTO lejos = punto("lejos", 6.22, -75.568);
        when(routingApiClient.route(any(), any(), anyList(), any())).thenReturn(ruta(900, 6000, null));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble())).thenReturn(prob(0.1));

        TripResponseDTO r = useCase.planificarViaje(7,
                request(List.of(lejos, cerca), TripRequestDTO.ModoParadas.OPTIMIZAR_RUTA, null));

        @SuppressWarnings("unchecked")
        ArgumentCaptor<List<LocationPointDTO>> enviadas = ArgumentCaptor.forClass(List.class);
        verify(routingApiClient).route(any(), any(), enviadas.capture(), any());
        assertThat(enviadas.getValue()).containsExactly(cerca, lejos);
        assertThat(r.getParadasOrdenadas()).containsExactly(cerca, lejos);
        verify(paradaRepo).saveAll(99, List.of(cerca, lejos));
    }

    @Test
    @DisplayName("ORDEN_INGRESADO: se respeta el orden recibido")
    void paradasEnOrden() {
        LocationPointDTO cerca = punto("cerca", 6.24, -75.568);
        LocationPointDTO lejos = punto("lejos", 6.22, -75.568);
        when(routingApiClient.route(any(), any(), anyList(), any())).thenReturn(ruta(900, 6000, null));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble())).thenReturn(prob(0.1));

        TripResponseDTO r = useCase.planificarViaje(7, request(List.of(lejos, cerca), null, null));

        assertThat(r.getParadasOrdenadas()).containsExactly(lejos, cerca);
    }

    @Test
    @DisplayName("un punto sin coordenadas (placeId heredado) → 400 sin llamar a rutas")
    void sinCoordenadas() {
        TripRequestDTO req = TripRequestDTO.builder()
                .origen(LocationPointDTO.builder().placeId("ChIJ-legado").build()).destino(DESTINO).build();

        assertThatThrownBy(() -> useCase.planificarViaje(7, req))
                .isInstanceOf(IllegalArgumentException.class).hasMessageContaining("lat y lng");
        verifyNoInteractions(routingApiClient);
    }

    @Test
    @DisplayName("routing service caído o sin ruta → se propaga y no se persiste nada")
    void erroresNoPersisten() {
        when(routingApiClient.route(any(), any(), anyList(), any()))
                .thenThrow(new RoutingUnavailableException("caído", null))
                .thenThrow(new NoRouteException("sin ruta", null));

        assertThatThrownBy(() -> useCase.planificarViaje(7, request(null, null, null)))
                .isInstanceOf(RoutingUnavailableException.class);
        assertThatThrownBy(() -> useCase.planificarViaje(7, request(null, null, null)))
                .isInstanceOf(NoRouteException.class);
        verify(viajeRepository, never()).save(any());
    }

    @Test
    @DisplayName("si la predicción falla no se inventa una probabilidad ni se persiste")
    void prediccionFalla() {
        when(routingApiClient.route(any(), any(), anyList(), any())).thenReturn(ruta(600, 4000, null));
        when(weatherMLService.predictRainForLocation(anyDouble(), anyDouble()))
                .thenThrow(new IllegalStateException("El ML API rechazó la petición"));

        assertThatThrownBy(() -> useCase.planificarViaje(7, request(null, null, null)))
                .isInstanceOf(IllegalStateException.class);
        verify(viajeRepository, never()).save(any());
    }
}
