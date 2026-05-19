package ti.mdva.service;

import java.util.List;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RouteStepDTO;
import ti.mdva.model.dto.TripResponseDTO;

/**
 * Puerto (interfaz) para comunicación con Google Maps Platform.
 * Agrupa Directions API y Geocoding API.
 */
public interface GoogleMapsService {

    /**
     * Resuelve un placeId a coordenadas lat/lng usando Geocoding API.
     * Si la LocationPoint ya tiene lat/lng, las retorna directamente.
     *
     * @param point LocationPointDTO con placeId o coordenadas
     * @return LocationPointDTO con lat/lng garantizados
     */
    LocationPointDTO resolveCoordinates(LocationPointDTO point);

    /**
     * Obtiene la ruta óptima entre dos puntos usando Directions API,
     * soportando paradas intermedias (waypoints).
     *
     * @param origin              punto de origen (con lat/lng resueltos)
     * @param destination         punto de destino (con lat/lng resueltos)
     * @param waypoints           lista opcional de paradas intermedias
     * @param optimizeWaypoints   si Google debe reordenar las paradas
     * @param travelMode          "driving" o "bicycling"
     * @param avoidTunelOriente   si true, inyecta un waypoint de desvío cuando la ruta cruza el Túnel de Oriente
     * @return RouteResult con duración, distancia, polyline y pasos
     */
    RouteResult getOptimalRoute(LocationPointDTO origin, LocationPointDTO destination, List<LocationPointDTO> waypoints, boolean optimizeWaypoints, String travelMode, boolean avoidTunelOriente);

    /**
     * Resultado de una consulta a Directions API.
     */
    record RouteResult(
            int durationSeconds,
            int distanceMeters,
            String overviewPolyline,
            List<RouteStepDTO> steps,
            List<Integer> waypointOrder
    ) {}
}
