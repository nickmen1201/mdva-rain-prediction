package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RouteStepDTO;
import ti.mdva.service.GoogleApiErrorTranslator;
import ti.mdva.service.GoogleMapsService;

import java.util.ArrayList;
import java.util.List;

/**
 * Implementación de GoogleMapsService usando las APIs REST de Google Maps Platform.
 *
 * Endpoints utilizados:
 *  - Geocoding API:   https://maps.googleapis.com/maps/api/geocode/json
 *  - Directions API:  https://maps.googleapis.com/maps/api/directions/json
 *
 * Configurar en application.yml:
 *   google.maps.api-key: ${GOOGLE_MAPS_API_KEY}
 */
@Slf4j
@Service
public class GoogleMapsServiceImpl implements GoogleMapsService {

    private static final String GEOCODING_URL   = "https://maps.googleapis.com/maps/api/geocode/json";
    private static final String DIRECTIONS_URL  = "https://maps.googleapis.com/maps/api/directions/json";

    private final RestTemplate restTemplate;
    private final String apiKey;

    public GoogleMapsServiceImpl(@Value("${google.maps.api-key}") String apiKey) {
        this.restTemplate = new RestTemplate();
        this.apiKey       = apiKey;
    }

    // ── Resolución de coordenadas ──────────────────────────────────────────────

    @Override
    public LocationPointDTO resolveCoordinates(LocationPointDTO point) {
        // Si ya tiene coordenadas, no hace falta geocodificar
        if (point.getLat() != null && point.getLng() != null) {
            return point;
        }

        if (point.getPlaceId() == null || point.getPlaceId().isBlank()) {
            throw new IllegalArgumentException(
                "Se necesita placeId o lat/lng para resolver coordenadas."
            );
        }

        String url = UriComponentsBuilder.fromHttpUrl(GEOCODING_URL)
                .queryParam("place_id", point.getPlaceId())
                .queryParam("key", apiKey)
                .toUriString();

        JsonNode response = restTemplate.getForObject(url, JsonNode.class);

        if (response == null || !"OK".equals(response.path("status").asText())) {
            String status = response != null ? response.path("status").asText() : "NULL_RESPONSE";
            log.error("Geocoding API error para placeId={} status={}", point.getPlaceId(), status);
            throw new RuntimeException(GoogleApiErrorTranslator.traducir(status, true));
        }

        JsonNode location = response
                .path("results").get(0)
                .path("geometry")
                .path("location");

        return LocationPointDTO.builder()
                .placeId(point.getPlaceId())
                .displayName(point.getDisplayName())
                .lat(location.path("lat").asDouble())
                .lng(location.path("lng").asDouble())
                .build();
    }

    // ── Ruta óptima ───────────────────────────────────────────────────────────

    @Override
    public RouteResult getOptimalRoute(LocationPointDTO origin, LocationPointDTO destination, List<LocationPointDTO> waypoints, boolean optimizeWaypoints, String travelMode, boolean avoidTunelOriente) {
        String originParam      = origin.getLat()      + "," + origin.getLng();
        String destinationParam = destination.getLat() + "," + destination.getLng();

        UriComponentsBuilder builder = UriComponentsBuilder.fromHttpUrl(DIRECTIONS_URL)
                .queryParam("origin",      originParam)
                .queryParam("destination", destinationParam)
                .queryParam("mode",        travelMode)
                .queryParam("language",    "es")
                .queryParam("region",      "CO")
                .queryParam("key",         apiKey);

        // departure_time solo es válido para driving; bicycling/walking lo rechazan con ZERO_RESULTS
        if ("driving".equals(travelMode)) {
            builder.queryParam("departure_time", "now");
        }

        // El Túnel de Oriente es un peaje: avoid=tolls hace que Google lo evite de forma nativa.
        if (avoidTunelOriente) {
            builder.queryParam("avoid", "tolls");
            log.info("Moto: solicitando ruta sin peajes (evita Tunel de Oriente)");
        }

        // Waypoints se construyen fuera del builder para evitar doble codificación de '|'.
        // UriComponentsBuilder convierte '|' → '%7C', y luego RestTemplate re-codifica
        // '%' → '%25', produciendo '%257C' que Google Maps no reconoce.
        List<String> wpStrings = new ArrayList<>();

        if (waypoints != null && !waypoints.isEmpty()) {
            for (LocationPointDTO wp : waypoints) {
                if (wp.getLat() != null && wp.getLng() != null) {
                    wpStrings.add(wp.getLat() + "," + wp.getLng());
                } else if (wp.getPlaceId() != null) {
                    wpStrings.add("place_id:" + wp.getPlaceId());
                }
            }
        }

        String url = builder.toUriString();
        if (!wpStrings.isEmpty()) {
            String optimizePrefix = optimizeWaypoints ? "optimize:true%7C" : "";
            url += "&waypoints=" + optimizePrefix + String.join("%7C", wpStrings);
        }

        JsonNode response = restTemplate.getForObject(java.net.URI.create(url), JsonNode.class);

        if (response == null || !"OK".equals(response.path("status").asText())) {
            String status = response != null ? response.path("status").asText() : "NULL_RESPONSE";
            log.error("Directions API error: {}", status);
            throw new RuntimeException(GoogleApiErrorTranslator.traducir(status, false));
        }

        JsonNode routeNode = response.path("routes").get(0);
        JsonNode legs = routeNode.path("legs");

        int totalDurationSeconds = 0;
        int totalDistanceMeters = 0;
        List<RouteStepDTO> allSteps = new ArrayList<>();

        for (JsonNode leg : legs) {
            JsonNode durationNode = leg.has("duration_in_traffic")
                    ? leg.path("duration_in_traffic")
                    : leg.path("duration");

            totalDurationSeconds += durationNode.path("value").asInt();
            totalDistanceMeters += leg.path("distance").path("value").asInt();

            allSteps.addAll(parseSteps(leg.path("steps")));
        }

        String overviewPolyline = routeNode.path("overview_polyline").path("points").asText();
        List<Integer> waypointOrder = parseWaypointOrder(routeNode.path("waypoint_order"));

        log.debug("Ruta calculada: {}m, {}s, {} pasos", totalDistanceMeters, totalDurationSeconds, allSteps.size());

        return new RouteResult(totalDurationSeconds, totalDistanceMeters, overviewPolyline, allSteps, waypointOrder);
    }

    // ── Helpers ───────────────────────────────────────────────────────────────

    private List<RouteStepDTO> parseSteps(JsonNode stepsNode) {
        List<RouteStepDTO> result = new ArrayList<>();
        if (stepsNode == null || !stepsNode.isArray()) return result;

        for (JsonNode step : stepsNode) {
            // html_instructions viene con tags HTML; los limpiamos
            String instruccion = step.path("html_instructions").asText()
                    .replaceAll("<[^>]+>", " ")
                    .replaceAll("\\s+", " ")
                    .trim();

            result.add(RouteStepDTO.builder()
                    .instruccion(instruccion)
                    .distanciaMetros(step.path("distance").path("value").asInt())
                    .duracionSegundos(step.path("duration").path("value").asInt())
                    .startLat(step.path("start_location").path("lat").asDouble())
                    .startLng(step.path("start_location").path("lng").asDouble())
                    .endLat(step.path("end_location").path("lat").asDouble())
                    .endLng(step.path("end_location").path("lng").asDouble())
                    .build());
        }
        return result;
    }

    private List<Integer> parseWaypointOrder(JsonNode orderNode) {
        List<Integer> result = new ArrayList<>();
        if (orderNode == null || !orderNode.isArray()) return result;
        for (JsonNode item : orderNode) {
            result.add(item.asInt());
        }
        return result;
    }
}
