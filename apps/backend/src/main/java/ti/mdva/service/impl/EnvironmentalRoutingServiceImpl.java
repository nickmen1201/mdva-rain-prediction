package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RouteStepDTO;
import ti.mdva.service.EnvironmentalRoutingService;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

/**
 * Implementación de EnvironmentalRoutingService que llama al microservicio
 * FastAPI de enrutamiento ambiental (services/routing_api).
 *
 * Endpoint utilizado:
 *   POST http://routing-service:8000/api/v1/route/spring
 *
 * Este servicio reemplaza a Google Directions API con rutas calculadas
 * por OSMnx/NetworkX que ya integran variables ambientales (MDVA ML + SIATA).
 */
@Slf4j
@Service
public class EnvironmentalRoutingServiceImpl implements EnvironmentalRoutingService {

    private final RestTemplate restTemplate;
    private final String routingServiceUrl;

    public EnvironmentalRoutingServiceImpl(
            @Value("${routing.service.url:http://localhost:8000}") String routingServiceUrl
    ) {
        this.restTemplate = new RestTemplate();
        this.routingServiceUrl = routingServiceUrl;
    }

    @Override
    public EnvironmentalRouteResult getOptimalRoute(
            LocationPointDTO origin,
            LocationPointDTO destination,
            List<LocationPointDTO> waypoints
    ) {
        String endpoint = routingServiceUrl + "/api/v1/route/spring";

        // Construir payload compatible con SpringRouteRequest del FastAPI
        Map<String, Object> payload = new HashMap<>();
        payload.put("origen", Map.of(
                "latitude", origin.getLat(),
                "longitude", origin.getLng()
        ));
        payload.put("destino", Map.of(
                "latitude", destination.getLat(),
                "longitude", destination.getLng()
        ));
        payload.put("vehicle_type", "car");
        payload.put("route_type", "fastest");

        // Paradas intermedias
        if (waypoints != null && !waypoints.isEmpty()) {
            List<Map<String, Double>> paradasList = new ArrayList<>();
            for (LocationPointDTO wp : waypoints) {
                paradasList.add(Map.of(
                        "latitude", wp.getLat(),
                        "longitude", wp.getLng()
                ));
            }
            payload.put("paradas", paradasList);
        }

        log.debug("Llamando al servicio de enrutamiento ambiental: {}", endpoint);

        JsonNode response = restTemplate.postForObject(endpoint, payload, JsonNode.class);

        if (response == null) {
            throw new RuntimeException(
                    "El servicio de enrutamiento ambiental no respondió para " +
                    "origen=(%f,%f) destino=(%f,%f)".formatted(
                            origin.getLat(), origin.getLng(),
                            destination.getLat(), destination.getLng()
                    )
            );
        }

        // Parsear respuesta
        int durationSeconds = response.path("duracionSegundos").asInt();
        int distanceMeters  = response.path("distanciaMetros").asInt();
        String overviewPoly = response.path("overviewPolyline").asText("");

        // Parsear pasos de navegación
        List<RouteStepDTO> steps = new ArrayList<>();
        JsonNode pasosNode = response.path("pasos");
        if (pasosNode.isArray()) {
            for (JsonNode paso : pasosNode) {
                steps.add(RouteStepDTO.builder()
                        .instruccion(paso.path("instruccion").asText(""))
                        .distanciaMetros(paso.path("distanciaMetros").asInt(0))
                        .duracionSegundos(paso.path("duracionSegundos").asInt(0))
                        .startLat(paso.path("startLat").asDouble())
                        .startLng(paso.path("startLng").asDouble())
                        .endLat(paso.path("endLat").asDouble())
                        .endLng(paso.path("endLng").asDouble())
                        .build());
            }
        }

        // Variables ambientales
        double rainFactor         = response.path("rain_factor").asDouble(1.0);
        double rainProbability    = response.path("rain_probability").asDouble(0.0);
        double rainIntensityAvg   = response.path("rain_intensity_avg").asDouble(0.0);
        double elevationAvg       = response.path("elevation_avg").asDouble(1500.0);
        String routeType          = response.path("route_type").asText("fastest");
        boolean mdvaLlueve        = response.path("mdva_llueve").asBoolean(false);
        double mdvaProbRf         = response.path("mdva_probabilidad_rf").asDouble(0.0);
        double mdvaProbRl         = response.path("mdva_probabilidad_rl").asDouble(0.0);
        double mdvaTempC          = response.path("mdva_temperatura_c").asDouble(0.0);
        double mdvaHumPct         = response.path("mdva_humedad_pct").asDouble(0.0);
        double mdvaCloudPct       = response.path("mdva_cobertura_nubosa_pct").asDouble(0.0);
        double mdvaWindMs         = response.path("mdva_velocidad_viento_ms").asDouble(0.0);
        String alertaNivel        = response.path("alerta_nivel").asText("VERDE");
        String alertaMensaje      = response.path("alerta_mensaje").asText("");
        boolean sugerirAlterna    = response.path("sugerir_ruta_alterna").asBoolean(false);

        log.debug("Ruta ambiental calculada: {}m, {}s, tipo={}, alerta={}, llueve={}, probRF={}", 
                distanceMeters, durationSeconds, routeType, alertaNivel, mdvaLlueve, mdvaProbRf);

        return new EnvironmentalRouteResult(
                durationSeconds,
                distanceMeters,
                overviewPoly,
                steps,
                rainFactor,
                rainProbability,
                rainIntensityAvg,
                elevationAvg,
                routeType,
                mdvaLlueve,
                mdvaProbRf,
                mdvaProbRl,
                mdvaTempC,
                mdvaHumPct,
                mdvaCloudPct,
                mdvaWindMs,
                alertaNivel,
                alertaMensaje,
                sugerirAlterna
        );
    }

    @Override
    public EnvironmentalRouteResult getRoute(
            LocationPointDTO origin,
            LocationPointDTO destination,
            List<LocationPointDTO> waypoints,
            String routeType,
            String vehicleType
    ) {
        String endpoint = routingServiceUrl + "/api/v1/route/spring";

        Map<String, Object> payload = new HashMap<>();
        payload.put("origen", Map.of(
                "latitude", origin.getLat(),
                "longitude", origin.getLng()
        ));
        payload.put("destino", Map.of(
                "latitude", destination.getLat(),
                "longitude", destination.getLng()
        ));
        payload.put("vehicle_type", vehicleType != null ? vehicleType : "car");
        payload.put("route_type", routeType != null ? routeType : "fastest");

        if (waypoints != null && !waypoints.isEmpty()) {
            List<Map<String, Double>> paradasList = new ArrayList<>();
            for (LocationPointDTO wp : waypoints) {
                paradasList.add(Map.of(
                        "latitude", wp.getLat(),
                        "longitude", wp.getLng()
                ));
            }
            payload.put("paradas", paradasList);
        }

        log.debug("Llamando al servicio de enrutamiento ambiental ({}): {}", routeType, endpoint);

        JsonNode response = restTemplate.postForObject(endpoint, payload, JsonNode.class);

        if (response == null) {
            throw new RuntimeException(
                    "El servicio de enrutamiento ambiental no respondió para ruta " + routeType);
        }

        int durationSeconds = response.path("duracionSegundos").asInt();
        int distanceMeters  = response.path("distanciaMetros").asInt();
        String overviewPoly = response.path("overviewPolyline").asText("");

        List<RouteStepDTO> steps = new ArrayList<>();
        JsonNode pasosNode = response.path("pasos");
        if (pasosNode.isArray()) {
            for (JsonNode paso : pasosNode) {
                steps.add(RouteStepDTO.builder()
                        .instruccion(paso.path("instruccion").asText(""))
                        .distanciaMetros(paso.path("distanciaMetros").asInt(0))
                        .duracionSegundos(paso.path("duracionSegundos").asInt(0))
                        .startLat(paso.path("startLat").asDouble())
                        .startLng(paso.path("startLng").asDouble())
                        .endLat(paso.path("endLat").asDouble())
                        .endLng(paso.path("endLng").asDouble())
                        .build());
            }
        }

        double rainFactor      = response.path("rain_factor").asDouble(1.0);
        double rainProbability = response.path("rain_probability").asDouble(0.0);
        double rainIntensityAvg= response.path("rain_intensity_avg").asDouble(0.0);
        double elevationAvg    = response.path("elevation_avg").asDouble(1500.0);
        String rType           = response.path("route_type").asText(routeType);
        boolean mdvaLlueve     = response.path("mdva_llueve").asBoolean(false);
        double mdvaProbRf      = response.path("mdva_probabilidad_rf").asDouble(0.0);
        double mdvaProbRl      = response.path("mdva_probabilidad_rl").asDouble(0.0);
        double mdvaTempC       = response.path("mdva_temperatura_c").asDouble(0.0);
        double mdvaHumPct      = response.path("mdva_humedad_pct").asDouble(0.0);
        double mdvaCloudPct    = response.path("mdva_cobertura_nubosa_pct").asDouble(0.0);
        double mdvaWindMs      = response.path("mdva_velocidad_viento_ms").asDouble(0.0);
        String alertaNivel     = response.path("alerta_nivel").asText("VERDE");
        String alertaMensaje   = response.path("alerta_mensaje").asText("");
        boolean sugerirAlterna = response.path("sugerir_ruta_alterna").asBoolean(false);

        return new EnvironmentalRouteResult(
                durationSeconds, distanceMeters, overviewPoly, steps,
                rainFactor, rainProbability, rainIntensityAvg, elevationAvg,
                rType, mdvaLlueve, mdvaProbRf, mdvaProbRl,
                mdvaTempC, mdvaHumPct, mdvaCloudPct, mdvaWindMs,
                alertaNivel, alertaMensaje, sugerirAlterna
        );
    }

    @Override
    public EnvironmentalMetricsResult getEnvironmentalMetrics(LocationPointDTO origin) {
        String endpoint = routingServiceUrl + "/api/v1/route/metrics";

        Map<String, Object> payload = new HashMap<>();
        payload.put("origen", Map.of(
                "latitude", origin.getLat(),
                "longitude", origin.getLng()
        ));
        payload.put("destino", Map.of(
                "latitude", origin.getLat(), // No importa para métricas
                "longitude", origin.getLng()
        ));
        payload.put("vehicle_type", "car");

        log.debug("Llamando a métricas ambientales: {}", endpoint);

        JsonNode response = restTemplate.postForObject(endpoint, payload, JsonNode.class);

        if (response == null) {
            throw new RuntimeException("El servicio de enrutamiento ambiental no respondió para métricas.");
        }

        double rainFactor       = response.path("penalty").asDouble(1.0);
        double rainProbability  = response.path("probability").asDouble(0.0);
        double rainIntensityAvg = response.path("intensity").asDouble(0.0);
        double elevationAvg     = response.path("elevation").asDouble(1500.0);
        
        JsonNode mdva = response.path("mdva");
        boolean mdvaLlueve      = mdva.path("llueve").asBoolean(false);
        double mdvaProbRf       = mdva.path("probabilidad_rf").asDouble(0.0);
        double mdvaProbRl       = mdva.path("probabilidad_rl").asDouble(0.0);
        double mdvaTempC        = mdva.path("temperatura_c").asDouble(0.0);
        double mdvaHumPct       = mdva.path("humedad_pct").asDouble(0.0);
        double mdvaCloudPct     = mdva.path("cobertura_nubosa_pct").asDouble(0.0);
        double mdvaWindMs       = mdva.path("velocidad_viento_ms").asDouble(0.0);

        return new EnvironmentalMetricsResult(
                rainFactor,
                rainProbability,
                rainIntensityAvg,
                elevationAvg,
                mdvaLlueve,
                mdvaProbRf,
                mdvaProbRl,
                mdvaTempC,
                mdvaHumPct,
                mdvaCloudPct,
                mdvaWindMs
        );
    }
}
