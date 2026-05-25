package ti.mdva.usecases;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.*;
import ti.mdva.repositories.ViajeRepositoryImpl;
import ti.mdva.service.GoogleMapsService;
import ti.mdva.service.EnvironmentalRoutingService;
import ti.mdva.service.TripPlannerOrchestrator;
import ti.mdva.service.WeatherMLService;
import ti.mdva.repositories.VehiculoRepositoryImpl;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Optional;

/**
 * UseCase principal de viajes.
 *
 * Flujo de planificarViaje() (INTEGRADO CON ENRUTAMIENTO AMBIENTAL):
 *   1. Resolver coordenadas de origen y destino (Geocoding API si vienen como placeId)
 *   2. Intentar ruta con Enrutamiento Ambiental (OSMnx + MDVA ML + SIATA)
 *      - Si el servicio está disponible: la ruta ya incluye variables ambientales
 *      - Si falla: fallback a Google Directions + ML por separado
 *   3. Aplicar lógica de ajuste (TripPlannerOrchestrator)
 *   4. Persistir el viaje en base de datos
 *   5. Retornar TripResponseDTO enriquecido al controller
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
    private final EnvironmentalRoutingService environmentalRoutingService;
    private final WeatherMLService    weatherMLService;
    private final ti.mdva.repositories.CondicionesSnapshotRepository snapshotRepo;
    private final ti.mdva.repositories.ParadaViajeRepository paradaRepo;

    public ViajeUseCase(
            ViajeRepositoryImpl viajeRepository,
            VehiculoRepositoryImpl vehiculoRepository,
            GoogleMapsService googleMapsService,
            EnvironmentalRoutingService environmentalRoutingService,
            WeatherMLService weatherMLService,
            ti.mdva.repositories.CondicionesSnapshotRepository snapshotRepo,
            ti.mdva.repositories.ParadaViajeRepository paradaRepo
    ) {
        this.viajeRepository    = viajeRepository;
        this.vehiculoRepository = vehiculoRepository;
        this.googleMapsService  = googleMapsService;
        this.environmentalRoutingService = environmentalRoutingService;
        this.weatherMLService   = weatherMLService;
        this.snapshotRepo       = snapshotRepo;
        this.paradaRepo         = paradaRepo;
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

        // 2. Resolver paradas (waypoints)
        List<LocationPointDTO> waypoints = null;
        if (request.getParadas() != null && !request.getParadas().isEmpty()) {
            waypoints = request.getParadas().stream()
                    .map(googleMapsService::resolveCoordinates)
                    .toList();
        }

        TripRequestDTO.ModoParadas modoParadas = request.getModoParadas() != null
                ? request.getModoParadas()
                : TripRequestDTO.ModoParadas.ORDEN_INGRESADO;
        boolean optimizarParadas = modoParadas == TripRequestDTO.ModoParadas.OPTIMIZAR_RUTA;

        // Parámetros de ruta por tipo de vehículo
        TripRequestDTO.TipoVehiculo tipoVehiculo = request.getTipoVehiculo() != null
                ? request.getTipoVehiculo()
                : TripRequestDTO.TipoVehiculo.CARRO;
        String travelMode        = tipoVehiculo == TripRequestDTO.TipoVehiculo.BICICLETA ? "bicycling" : "driving";
        boolean avoidTunelOriente = tipoVehiculo == TripRequestDTO.TipoVehiculo.MOTO;

        // Mapear TipoVehiculo → vehicle_type del routing service
        String vehicleTypeStr = switch (tipoVehiculo) {
            case MOTO      -> "moto";
            case BICICLETA -> "bicycle";
            default        -> "car";
        };

        // 3. Ruta con Google Maps para tráfico en tiempo real y waypoints
        GoogleMapsService.RouteResult route = googleMapsService.getOptimalRoute(origen, destino, waypoints, optimizarParadas, travelMode, avoidTunelOriente);
        List<LocationPointDTO> paradasOrdenadas = ordenarWaypoints(waypoints, route.waypointOrder());
        int tiempoBaseMin = (int) Math.ceil(route.durationSeconds() / 60.0);

        // Motos son más ágiles en tráfico urbano: ajuste de -15 % sobre el tiempo de Google
        if (tipoVehiculo == TripRequestDTO.TipoVehiculo.MOTO) {
            tiempoBaseMin = (int) Math.ceil(tiempoBaseMin * 0.85);
        }

        log.debug("Ruta: {}m, {}min, {} pasos", route.distanceMeters(), tiempoBaseMin, route.steps().size());

        // 4. OBTENER MÉTRICAS AMBIENTALES (Python: ML + SIATA + Open-Meteo)
        RainPredictionDTO prediccion;
        String rutaAlternaPolyline = null;
        Integer rutaAlternaTiempoMin = null;
        String rutaAlternaTipo = null;

        try {
            log.info("Obteniendo métricas ambientales para enriquecer ruta de Google...");
            EnvironmentalRoutingService.EnvironmentalMetricsResult metrics =
                    environmentalRoutingService.getEnvironmentalMetrics(origen);

            prediccion = RainPredictionDTO.builder()
                    .llueve(metrics.mdvaLlueve())
                    .probabilidadRf(metrics.mdvaProbabilidadRf())
                    .probabilidadRl(metrics.mdvaProbabilidadRl())
                    .temperaturaC(metrics.mdvaTemperaturaC())
                    .humedadPct(metrics.mdvaHumedadPct())
                    .coberturaAnubosaPct(metrics.mdvaCoberturaNubosaPct())
                    .velocidadVientoMs(metrics.mdvaVelocidadVientoMs())
                    .build();

            tiempoBaseMin = (int) Math.ceil(tiempoBaseMin * metrics.rainFactor());

            log.info("Métricas obtenidas: probRF={}, factor_lluvia={}, elevacion={}",
                    metrics.mdvaProbabilidadRf(), metrics.rainFactor(), metrics.elevationAvg());

            // 4b. Si lluvia > 40%, calcular ruta más seca como alternativa
            if (metrics.mdvaProbabilidadRf() > 0.40) {
                try {
                    log.info("Lluvia > 40% — calculando ruta 'dryest' alternativa...");
                    EnvironmentalRoutingService.EnvironmentalRouteResult driest =
                            environmentalRoutingService.getRoute(origen, destino, waypoints, "dryest", vehicleTypeStr);
                    rutaAlternaPolyline  = driest.overviewPolyline();
                    rutaAlternaTiempoMin = (int) Math.ceil(driest.durationSeconds() / 60.0);
                    rutaAlternaTipo      = "dryest";
                    log.info("Ruta dryest: {}m en {}min", driest.distanceMeters(), rutaAlternaTiempoMin);
                } catch (Exception ex) {
                    log.warn("No se pudo obtener ruta dryest ({}), se omite", ex.getMessage());
                }
            }

        } catch (Exception e) {
            log.warn("Métricas ambientales no disponibles ({}), fallback a ML clásico", e.getMessage());
            prediccion = weatherMLService.predictRainForLocation(origen.getLat(), origen.getLng());
        }

        // 5. Ajuste por lluvia (TripPlannerOrchestrator)
        TripResponseDTO.TripResponseDTOBuilder builder = TripResponseDTO.builder()
                .origen(origen)
                .destino(destino)
                .paradasOrdenadas(paradasOrdenadas)
                .modoParadas(modoParadas)
                .tiempoBaseMin(tiempoBaseMin)
                .distanciaMetros(route.distanceMeters())
                .overviewPolyline(route.overviewPolyline())
                .pasos(route.steps())
                .rutaAlternaPolyline(rutaAlternaPolyline)
                .rutaAlternaTiempoMin(rutaAlternaTiempoMin)
                .rutaAlternaTipo(rutaAlternaTipo);

        TripPlannerOrchestrator.apply(builder, prediccion, tiempoBaseMin, route.distanceMeters());
        TripResponseDTO response = builder.build();

        // 5. Persistir
        Viajes saved = viajeRepository.save(buildViajeEntity(idUsuario, request, origen, destino, response));

        log.info("Viaje {} planificado: {}min base → {}min ajustado, alerta={}",
                saved.getIdViaje(),
                response.getTiempoBaseMin(),
                response.getTiempoEstimadoMin(),
                response.getAlertaNivel());

        // 5.1 Guardar snapshot para monitoreo (Sprint 5.2A)
        snapshotRepo.save(
                saved.getIdViaje(),
                prediccion.getProbabilidadRf() != null ? prediccion.getProbabilidadRf() : 0.0,
                prediccion.getProbabilidadRl() != null ? prediccion.getProbabilidadRl() : 0.0,
                prediccion.getTemperaturaC(),
                prediccion.getHumedadPct(),
                prediccion.getCoberturaAnubosaPct(),
                prediccion.getVelocidadVientoMs(),
                response.getAlertaNivel() != null ? response.getAlertaNivel().name() : "VERDE",
                OffsetDateTime.now() // idealmente vendría de weather API, usamos now()
        );

        // 5.2 Guardar paradas (Sprint 5.3)
        if (paradasOrdenadas != null && !paradasOrdenadas.isEmpty()) {
            paradaRepo.saveAll(saved.getIdViaje(), paradasOrdenadas);
        }

        // 6. Retornar DTO completo con el ID generado por la BD y las paradas
        // recién persistidas (con su id_parada y orden asignado por la BD).
        var paradasGuardadas = paradaRepo.findByViajeId(saved.getIdViaje());

        return response.toBuilder()
                .idViaje(saved.getIdViaje())
                .horaInicio(saved.getHoraInicio())
                .paradas(paradasGuardadas)
                .build();
    }

    /**
     * Lista las paradas intermedias de un viaje (Sprint 5.3).
     * Verifica pertenencia del viaje al usuario por seguridad.
     */
    public List<ParadaDTO> obtenerParadas(Integer idViaje, Integer idUsuario) {
        validarViajePertenece(idViaje, idUsuario);
        return paradaRepo.findByViajeId(idViaje);
    }

    /**
     * Marca una parada como finalizada (V6 + Sprint 5.3).
     * Caso de uso: el frontend detecta que el conductor está a <100m de la parada
     * y dispara este endpoint, o el usuario confirma manualmente desde el HUD.
     *
     * @throws IllegalArgumentException si la parada no existe
     */
    public void finalizarParada(Integer idViaje, Integer orden, Integer idUsuario) {
        validarViajePertenece(idViaje, idUsuario);
        boolean ok = paradaRepo.marcarParadaFinalizada(idViaje, orden);
        if (!ok) {
            throw new IllegalArgumentException(
                    "No existe parada con orden=" + orden + " en el viaje " + idViaje);
        }
        log.info("Parada finalizada: viaje={} orden={}", idViaje, orden);
    }

    private void validarViajePertenece(Integer idViaje, Integer idUsuario) {
        Viajes viaje = viajeRepository.findById(idViaje)
                .orElseThrow(() -> new IllegalArgumentException(
                        "No se encontró un viaje con id: " + idViaje));
        if (!viaje.getIdUsuario().equals(idUsuario)) {
            // Mismo mensaje que "no existe" para no revelar IDs ajenos
            throw new IllegalArgumentException(
                    "No se encontró un viaje con id: " + idViaje);
        }
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

    // ── Alerta en tiempo real (HU031) ─────────────────────────────────────────

    /**
     * Recalcula el clima sobre el origen del viaje y devuelve la alerta actualizada.
     *
     * No vuelve a llamar a Google Directions: la ruta y la distancia ya están
     * persistidas en BD. Solo cambia la predicción de lluvia y, por tanto,
     * el nivel de alerta y la sugerencia de ruta alterna.
     *
     * @throws IllegalArgumentException si el viaje no existe o no pertenece al usuario
     */
    public AlertaActualDTO obtenerAlertaActual(Integer idViaje, Integer idUsuario) {
        Viajes viaje = viajeRepository.findById(idViaje)
                .orElseThrow(() -> new IllegalArgumentException(
                        "No se encontró un viaje con id: " + idViaje));

        // Por seguridad, mismo mensaje que "no existe" para no revelar IDs ajenos
        if (!viaje.getIdUsuario().equals(idUsuario)) {
            throw new IllegalArgumentException(
                    "No se encontró un viaje con id: " + idViaje);
        }

        if (viaje.getLatOrigen() == null || viaje.getLngOrigen() == null) {
            throw new IllegalStateException(
                    "El viaje no tiene coordenadas de origen registradas (¿viaje legado pre-V2?)");
        }

        RainPredictionDTO prediccion = weatherMLService.predictRainForLocation(
                viaje.getLatOrigen(), viaje.getLngOrigen());

        // Reutilizamos el orchestrator pasándole un builder temporal.
        // tiempoBaseMin=1 es placeholder: solo nos interesa nivel/factor/alterna/mensaje.
        Integer distancia = viaje.getDistanciaMetros() != null ? viaje.getDistanciaMetros() : 0;
        TripResponseDTO.TripResponseDTOBuilder builder = TripResponseDTO.builder();
        TripPlannerOrchestrator.apply(builder, prediccion, 1, distancia);
        TripResponseDTO calc = builder.build();

        return AlertaActualDTO.builder()
                .idViaje(idViaje)
                .calculadoEn(OffsetDateTime.now())
                .alertaNivel(calc.getAlertaNivel())
                .alertaMensaje(calc.getAlertaMensaje())
                .factorAjuste(calc.getFactorAjuste())
                .sugerirRutaAlterna(calc.getSugerirRutaAlterna())
                .razonRutaAlterna(calc.getRazonRutaAlterna())
                .prediccionLluvia(prediccion)
                .build();
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

    private List<LocationPointDTO> ordenarWaypoints(List<LocationPointDTO> waypoints, List<Integer> waypointOrder) {
        if (waypoints == null || waypoints.isEmpty()) return List.of();
        if (waypointOrder == null || waypointOrder.isEmpty()) return waypoints;
        return waypointOrder.stream()
                .filter(i -> i >= 0 && i < waypoints.size())
                .map(waypoints::get)
                .toList();
    }

    private boolean puntosCercanos(LocationPointDTO a, LocationPointDTO b) {
        double dLat = Math.abs(a.getLat() - b.getLat());
        double dLng = Math.abs(a.getLng() - b.getLng());
        return dLat < 0.0005 && dLng < 0.0005;
    }
}
