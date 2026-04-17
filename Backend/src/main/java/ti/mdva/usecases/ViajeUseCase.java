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
import ti.mdva.repositories.VehiculoRepositoryImpl;

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
 * NOTA: Los campos lat/lng, nombres de lugar y distancia se persisten
 * en las columnas nativas agregadas en la migración V2 (lat_origen, lng_origen,
 * lat_destino, lng_destino, nombre_origen, nombre_destino, distancia_metros).
 */
@Service
public class ViajeUseCase {

    private static final Logger log = LoggerFactory.getLogger(ViajeUseCase.class);

    private final ViajeRepositoryImpl viajeRepository;
    private final VehiculoRepositoryImpl vehiculoRepository;
    private final GoogleMapsService   googleMapsService;
    private final WeatherMLService    weatherMLService;

    public ViajeUseCase(
            ViajeRepositoryImpl viajeRepository,
            VehiculoRepositoryImpl vehiculoRepository,
            GoogleMapsService googleMapsService,
            WeatherMLService weatherMLService
    ) {
        this.viajeRepository    = viajeRepository;
        this.vehiculoRepository = vehiculoRepository;
        this.googleMapsService  = googleMapsService;
        this.weatherMLService   = weatherMLService;
    }

    // ── Planificación ─────────────────────────────────────────────────────────

    public TripResponseDTO planificarViaje(Integer idUsuario, TripRequestDTO request) {

        // 1. Resolver coordenadas
        LocationPointDTO origen  = googleMapsService.resolveCoordinates(request.getOrigen());
        LocationPointDTO destino = googleMapsService.resolveCoordinates(request.getDestino());

        log.debug("Origen resuelto: lat={} lng={}", origen.getLat(), origen.getLng());
        log.debug("Destino resuelto: lat={} lng={}", destino.getLat(), destino.getLng());

        // Validar vehículo opcional
        String idVehiculo = request.getIdVehiculo();
        if (idVehiculo != null && !idVehiculo.trim().isEmpty()) {
            if (!vehiculoRepository.existsByPlaca(idVehiculo.trim())) {
                log.warn("El vehículo {} no existe en la base de datos. Se omitirá y asignará nulo.", idVehiculo);
                request.setIdVehiculo(null);
            } else {
                request.setIdVehiculo(idVehiculo.trim());
            }
        } else {
            request.setIdVehiculo(null);
        }

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
        Viajes saved = viajeRepository.save(buildViajeEntity(idUsuario, request, origen, destino, response));

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

    public Viajes finalizarViaje(Integer idViaje, Short userRating) {
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
        if (userRating != null) {
            viaje.setUserRating(userRating);
        }
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
     * Construye la entidad Viajes con todos los campos disponibles tras la migración V2.
     */
    private Viajes buildViajeEntity(
            Integer idUsuario,
            TripRequestDTO request,
            LocationPointDTO origen,
            LocationPointDTO destino,
            TripResponseDTO response
    ) {
        Viajes v = new Viajes();
        v.setIdUsuario(idUsuario);
        v.setIdVehiculo(request.getIdVehiculo());

        v.setLatOrigen(origen.getLat());
        v.setLngOrigen(origen.getLng());
        v.setLatDestino(destino.getLat());
        v.setLngDestino(destino.getLng());
        v.setNombreOrigen(origen.getDisplayName());
        v.setNombreDestino(destino.getDisplayName());
        v.setDistanciaMetros(response.getDistanciaMetros());

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