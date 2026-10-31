package ti.mdva.service.routing;

import com.fasterxml.jackson.databind.JsonNode;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.RouteStepDTO;
import ti.mdva.model.dto.TripRequestDTO;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Cliente del routing service propio (contrato: specs/008-backend-routing-nominatim/contracts).
 * Solo lee la geometría y la duración base; los campos de lluvia que calcula el routing service
 * se ignoran (la alerta sale del modelo evaluado, spec 007).
 */
@Component
public class RoutingApiClient {

    private final RestTemplate restTemplate;
    private final String baseUrl;

    @Autowired
    public RoutingApiClient(RestTemplateBuilder builder, @Value("${routing.service.url}") String baseUrl) {
        // HTTP/1.1 explícito (ver spec 007: uvicorn descarta el cuerpo con "Upgrade: h2c").
        // Lectura de 60 s: la primera ruta tras arrancar carga el grafo del valle.
        this(builder.requestFactory(SimpleClientHttpRequestFactory.class)
                .connectTimeout(Duration.ofSeconds(5)).readTimeout(Duration.ofSeconds(60)).build(), baseUrl);
    }

    RoutingApiClient(RestTemplate restTemplate, String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    /** Valor de {@code vehicle_type} que acepta el routing service. */
    static String vehicleType(TripRequestDTO.TipoVehiculo tipo) {
        if (tipo == null) return "car";
        return switch (tipo) {
            case MOTO -> "motorcycle";
            case BICICLETA -> "bike";
            case CARRO -> "car";
        };
    }

    /**
     * Ruta más rápida que pasa por las paradas en el orden dado.
     *
     * @throws NoRouteException            si no hay ruta entre los puntos
     * @throws RoutingUnavailableException si el servicio no responde
     */
    public RouteResult route(LocationPointDTO origen, LocationPointDTO destino, List<LocationPointDTO> paradas,
                             TripRequestDTO.TipoVehiculo tipoVehiculo) {
        Map<String, Object> payload = new HashMap<>();
        payload.put("origen", coord(origen));
        payload.put("destino", coord(destino));
        if (paradas != null && !paradas.isEmpty()) {
            payload.put("paradas", paradas.stream().map(RoutingApiClient::coord).toList());
        }
        payload.put("vehicle_type", vehicleType(tipoVehiculo));
        payload.put("route_type", "fastest");

        JsonNode r;
        try {
            r = restTemplate.postForObject(baseUrl + "/api/v1/route/spring", payload, JsonNode.class);
        } catch (HttpStatusCodeException e) {
            if (e.getStatusCode().value() == HttpStatus.BAD_REQUEST.value()) {
                throw new NoRouteException("No existe una ruta entre los puntos indicados.", e);
            }
            throw new RoutingUnavailableException(
                    "El routing service respondió %d".formatted(e.getStatusCode().value()), e);
        } catch (ResourceAccessException e) {
            throw new RoutingUnavailableException("El routing service no respondió", e);
        }
        if (r == null) throw new RoutingUnavailableException("El routing service respondió vacío", null);

        String polyline = r.path("overviewPolyline").asText("");
        return new RouteResult(
                r.path("duracionSegundos").asInt(),
                r.path("distanciaMetros").asInt(),
                polyline,
                steps(r.path("pasos")),
                alternative(r.path("alternativas"), polyline));
    }

    private static Map<String, Double> coord(LocationPointDTO p) {
        return Map.of("latitude", p.getLat(), "longitude", p.getLng());
    }

    private static List<RouteStepDTO> steps(JsonNode pasos) {
        List<RouteStepDTO> out = new ArrayList<>();
        for (JsonNode p : pasos) {
            out.add(RouteStepDTO.builder()
                    .instruccion(p.path("instruccion").asText(""))
                    .distanciaMetros(p.path("distanciaMetros").asInt())
                    .duracionSegundos(p.path("duracionSegundos").asInt())
                    .startLat(p.path("startLat").asDouble())
                    .startLng(p.path("startLng").asDouble())
                    .endLat(p.path("endLat").asDouble())
                    .endLng(p.path("endLng").asDouble())
                    .build());
        }
        return out;
    }

    /**
     * Alternativa para el usuario (RF-14): la ruta más seca si el routing service la calculó (spec 010);
     * si no, la primera con geometría distinta de la principal.
     */
    private static RouteResult.Alternative alternative(JsonNode alternativas, String principal) {
        RouteResult.Alternative primera = null;
        for (JsonNode a : alternativas) {
            String poly = a.path("overviewPolyline").asText("");
            if (poly.isEmpty() || poly.equals(principal)) continue;
            RouteResult.Alternative alt = new RouteResult.Alternative(
                    a.path("route_type").asText("alternativa"),
                    a.path("duracionSegundos").asInt(),
                    a.path("distanciaMetros").asInt(),
                    poly);
            if ("dryest".equals(alt.routeType())) return alt;
            if (primera == null) primera = alt;
        }
        return primera;
    }
}
