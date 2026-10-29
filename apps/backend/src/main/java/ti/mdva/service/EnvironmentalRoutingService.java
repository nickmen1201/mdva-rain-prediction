package ti.mdva.service;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RouteStepDTO;

import java.util.List;

/**
 * Puerto (interfaz) para comunicación con el servicio de enrutamiento ambiental.
 * Reemplaza Google Directions API con rutas OSMnx que consideran variables ambientales.
 */
public interface EnvironmentalRoutingService {

    /**
     * Obtiene la ruta óptima entre dos puntos usando el servicio de enrutamiento ambiental.
     * Soporta paradas intermedias (waypoints).
     * 
     * A diferencia de Google Directions, esta ruta ya incluye:
     * - Penalización por lluvia (SIATA + MDVA ML)
     * - Factores topográficos (elevación)
     * - Rutas alternativas (fastest, shortest, dryest)
     *
     * @param origin      punto de origen (con lat/lng resueltos)
     * @param destination punto de destino (con lat/lng resueltos)
     * @param waypoints   lista opcional de paradas intermedias
     * @return RouteResult con duración, distancia, polyline, pasos y variables ambientales
     */
    EnvironmentalRouteResult getOptimalRoute(
            LocationPointDTO origin,
            LocationPointDTO destination,
            List<LocationPointDTO> waypoints
    );

    /**
     * Obtiene la ruta óptima con tipo de ruta y vehículo explícitos.
     *
     * @param origin       punto de origen
     * @param destination  punto de destino
     * @param waypoints    paradas intermedias
     * @param routeType    "fastest", "shortest" o "dryest"
     * @param vehicleType  "car", "moto", "bicycle" o "walk"
     */
    EnvironmentalRouteResult getRoute(
            LocationPointDTO origin,
            LocationPointDTO destination,
            List<LocationPointDTO> waypoints,
            String routeType,
            String vehicleType
    );

    /**
     * Obtiene únicamente las métricas ambientales (SIATA + MDVA ML + Open-Meteo) para un punto.
     * Ideal para enriquecer rutas generadas por otros motores (ej. Google Maps).
     */
    EnvironmentalMetricsResult getEnvironmentalMetrics(LocationPointDTO origin);

    /**
     * Resultado de métricas ambientales.
     */
    record EnvironmentalMetricsResult(
            double rainFactor,
            double rainProbability,
            double rainIntensityAvg,
            double elevationAvg,
            boolean mdvaLlueve,
            double mdvaProbabilidadRf,
            double mdvaProbabilidadRl,
            double mdvaTemperaturaC,
            double mdvaHumedadPct,
            double mdvaCoberturaNubosaPct,
            double mdvaVelocidadVientoMs
    ) {}

    /**
     * Resultado de una consulta al servicio de enrutamiento ambiental.
     * Extiende el RouteResult de Google con variables ambientales integradas.
     */
    record EnvironmentalRouteResult(
            int durationSeconds,
            int distanceMeters,
            String overviewPolyline,
            List<RouteStepDTO> steps,
            // ── Variables ambientales ──
            double rainFactor,
            double rainProbability,
            double rainIntensityAvg,
            double elevationAvg,
            String routeType,
            boolean mdvaLlueve,
            double mdvaProbabilidadRf,
            double mdvaProbabilidadRl,
            double mdvaTemperaturaC,
            double mdvaHumedadPct,
            double mdvaCoberturaNubosaPct,
            double mdvaVelocidadVientoMs,
            String alertaNivel,
            String alertaMensaje,
            boolean sugerirRutaAlterna
    ) {}
}
