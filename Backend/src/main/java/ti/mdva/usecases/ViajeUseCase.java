package ti.mdva.usecases;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.*;
import ti.mdva.repositories.ViajeRepositoryImpl;
import ti.mdva.service.GoogleMapsService;
import ti.mdva.service.TripPlannerOrchestrator;
import ti.mdva.service.WeatherMLService;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

/**
 * UseCase principal de viajes.
 *
 * Flujo de planificarViaje():
 *   1. Resolver coordenadas de origen y destino (Geocoding API si vienen como placeId)
 *   2. Calcular ruta óptima (Directions API → duración, distancia, polyline, pasos)
 *   3. Obtener predicción de lluvia (Open-Meteo → FastAPI ML)
 *   4. Aplicar lógica de ajuste (TripPlannerOrchestrator)
 *   5. Persistir el viaje en base de datos
 *   6. Retornar TripResponseDTO enriquecido al controller
 *
 * NOTA: Los campos lat/lng se guardan temporalmente como "lat,lng" en
 * idBarrioOrigen/idBarrioDestino hasta que se corra la migración V2 y se
 * regenere JOOQ. Una vez regenerado, actualizar buildViajeEntity() y el
 * ViajeRepositoryImpl.save() para usar los nuevos campos nativos.
 */
@Service
public class ViajeUseCase {

    private static final Logger log = LoggerFactory.getLogger(ViajeUseCase.class);

    private final ViajeRepositoryImpl viajeRepository;
    private final GoogleMapsService   googleMapsService;
    private final WeatherMLService    weatherMLService;

    public ViajeUseCase(
            ViajeRepositoryImpl viajeRepository,
            GoogleMapsService googleMapsService,
            WeatherMLService weatherMLService
    ) {
        this.viajeRepository   = viajeRepository;
        this.googleMapsService = googleMapsService;
        this.weatherMLService  = weatherMLService;
    }

    // ── Planificación ─────────────────────────────────────────────────────────

    public TripResponseDTO planificarViaje(TripRequestDTO request) {

        // 1. Resolver coordenadas
        LocationPointDTO origen  = googleMapsService.resolveCoordinates(request.getOrigen());
        LocationPointDTO destino = googleMapsService.resolveCoordinates(request.getDestino());

        log.debug("Origen resuelto: lat={} lng={}", origen.getLat(), origen.getLng());
        log.debug("Destino resuelto: lat={} lng={}", destino.getLat(), destino.getLng());

        if (puntosCercanos(origen, destino)) {
            throw new IllegalArgumentException("El origen y el destino no pueden ser el mismo lugar.");
        }

        // 2. Ruta óptima
        GoogleMapsService.RouteResult route = googleMapsService.getOptimalRoute(origen, destino);
        int tiempoBaseMin = (int) Math.ceil(route.durationSeconds() / 60.0);

        log.debug("Ruta: {}m, {}min, {} pasos", route.distanceMeters(), tiempoBaseMin, route.steps().size());

        // 3. Predicción de lluvia
        RainPredictionDTO prediccion = weatherMLService.predictRainForLocation(
                origen.getLat(), origen.getLng()
        );

        // 4. Ajuste por lluvia
        TripResponseDTO.TripResponseDTOBuilder builder = TripResponseDTO.builder()
                .origen(origen)
                .destino(destino)
                .tiempoBaseMin(tiempoBaseMin)
                .distanciaMetros(route.distanceMeters())
                .overviewPolyline(route.overviewPolyline())
                .pasos(route.steps());

        TripPlannerOrchestrator.apply(builder, prediccion, tiempoBaseMin, route.distanceMeters());

        TripResponseDTO response = builder.build();

        // 5. Persistir
        Viajes saved = viajeRepository.save(buildViajeEntity(request, origen, destino, response));

        log.info("Viaje {} planificado: {}min base → {}min ajustado, alerta={}",
                saved.getIdViaje(),
                tiempoBaseMin,
                response.getTiempoEstimadoMin(),
                response.getAlertaNivel());

        // 6. Retornar DTO completo con el ID generado por la BD
        return response.toBuilder()
                .idViaje(saved.getIdViaje())
                .horaInicio(saved.getHoraInicio())
                .build();
    }

    // ── Finalización ──────────────────────────────────────────────────────────

    public Viajes finalizarViaje(Integer idViaje) {
        Viajes viaje = viajeRepository.findById(idViaje)
                .orElseThrow(() -> new IllegalArgumentException(
                        "No se encontró un viaje con id: " + idViaje
                ));

        if (Boolean.TRUE.equals(viaje.getFinalizado())) {
            throw new IllegalStateException(
                    "El viaje con id " + idViaje + " ya fue finalizado."
            );
        }

        viaje.setFinalizado(true);
        viaje.setHoraFin(OffsetDateTime.now());
        return viajeRepository.save(viaje);
    }

    // ── Consultas ─────────────────────────────────────────────────────────────

    public Optional<Viajes> findById(Integer idViaje) {
        return viajeRepository.findById(idViaje);
    }

    public List<Viajes> findByUsuario(Integer idUsuario) {
        return viajeRepository.findByUsuario(idUsuario);
    }

    // ── Helpers privados ──────────────────────────────────────────────────────

    /**
     * Construye la entidad Viajes usando los campos existentes en el POJO actual.
     *
     * TEMPORAL: lat/lng se serializan como "lat,lng" en idBarrioOrigen/idBarrioDestino
     * hasta que se corra la migración V2 y se regenere JOOQ con los nuevos campos.
     */
    private Viajes buildViajeEntity(
            TripRequestDTO request,
            LocationPointDTO origen,
            LocationPointDTO destino,
            TripResponseDTO response
    ) {
        Viajes v = new Viajes();
        v.setIdUsuario(request.getIdUsuario());
        v.setIdVehiculo(request.getIdVehiculo());

        // TEMPORAL hasta regenerar JOOQ post-V2
        v.setIdBarrioOrigen(origen.getLat() + "," + origen.getLng());
        v.setIdBarrioDestino(destino.getLat() + "," + destino.getLng());

        v.setTiempoEstimadoMin(response.getTiempoEstimadoMin().shortValue());
        v.setPrecipitacionMm(calcularPrecipitacionMm(response.getPrediccionLluvia()));
        v.setHoraInicio(OffsetDateTime.now());
        v.setFinalizado(false);
        return v;
    }

    private short calcularPrecipitacionMm(RainPredictionDTO pred) {
        if (!Boolean.TRUE.equals(pred.getLlueve())) return 0;
        double prob = pred.getProbabilidadRf();
        if (prob < 0.55) return 2;
        if (prob < 0.70) return 5;
        return 10;
    }

    private boolean puntosCercanos(LocationPointDTO a, LocationPointDTO b) {
        double dLat = Math.abs(a.getLat() - b.getLat());
        double dLng = Math.abs(a.getLng() - b.getLng());
        return dLat < 0.0005 && dLng < 0.0005;
    }
}