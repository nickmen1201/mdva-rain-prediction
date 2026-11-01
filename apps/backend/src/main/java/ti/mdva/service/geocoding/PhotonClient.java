package ti.mdva.service.geocoding;

import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Sugerencias mientras se escribe con Photon (geocodificador sobre datos OSM pensado para
 * búsqueda incremental, https://photon.komoot.io). Nominatim público no permite consultas
 * por tecla; por eso las sugerencias vienen de Photon y la búsqueda completa sigue en
 * {@link NominatimClient}. Resultados limitados al Valle de Aburrá y sesgados hacia Medellín.
 */
@Slf4j
@Component
public class PhotonClient {

    /** Valle de Aburrá: lon mín, lat mín, lon máx, lat máx (orden de Photon). */
    static final String BBOX = "-75.72,6.00,-75.30,6.55";
    static final double BIAS_LAT = 6.2442;
    static final double BIAS_LON = -75.5812;
    static final Duration TTL = Duration.ofMinutes(30);
    static final int MAX_CACHE = 2_000;
    static final int LIMIT = 5;

    private record Cached(List<GeocodingResultDTO> value, Instant expiresAt) {}

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final String userAgent;
    private final Clock clock;
    private final Map<String, Cached> cache = new ConcurrentHashMap<>();

    @Autowired
    public PhotonClient(RestTemplateBuilder builder,
                        @Value("${geocoding.photon.url}") String baseUrl,
                        @Value("${geocoding.nominatim.user-agent}") String userAgent) {
        this(builder.connectTimeout(Duration.ofSeconds(3)).readTimeout(Duration.ofSeconds(5)).build(),
                baseUrl, userAgent, Clock.systemUTC());
    }

    PhotonClient(RestTemplate restTemplate, String baseUrl, String userAgent, Clock clock) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.userAgent = userAgent;
        this.clock = clock;
    }

    /** Hasta 5 lugares del Valle de Aburrá que empiezan a coincidir con el texto parcial. */
    public List<GeocodingResultDTO> suggest(String query) {
        String key = NominatimClient.normalize(query);
        if (key.length() < 3) {
            throw new IllegalArgumentException("La búsqueda debe tener al menos 3 caracteres.");
        }
        Instant now = clock.instant();
        Cached hit = cache.get(key);
        if (hit != null && now.isBefore(hit.expiresAt())) return hit.value();

        URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/api/")
                .queryParam("q", query.trim())
                .queryParam("limit", LIMIT)
                .queryParam("bbox", BBOX)
                .queryParam("lat", BIAS_LAT)
                .queryParam("lon", BIAS_LON)
                .encode().build().toUri();
        List<GeocodingResultDTO> out = toResults(call(uri));

        if (cache.size() >= MAX_CACHE) cache.values().removeIf(c -> !now.isBefore(c.expiresAt()));
        if (cache.size() < MAX_CACHE) cache.put(key, new Cached(out, now.plus(TTL)));
        return out;
    }

    private JsonNode call(URI uri) {
        HttpHeaders headers = new HttpHeaders();
        headers.set(HttpHeaders.USER_AGENT, userAgent);
        try {
            JsonNode body = restTemplate.exchange(uri, HttpMethod.GET, new HttpEntity<>(headers), JsonNode.class)
                    .getBody();
            if (body == null) throw new GeocodingUnavailableException("Photon respondió vacío", null);
            return body;
        } catch (RestClientException e) {
            log.warn("Photon falló: {}", e.getMessage());
            throw new GeocodingUnavailableException("Photon no respondió", e);
        }
    }

    /** GeoJSON de Photon → resultados con nombre legible, sin duplicados. */
    static List<GeocodingResultDTO> toResults(JsonNode body) {
        List<GeocodingResultDTO> out = new ArrayList<>();
        Set<String> vistos = new LinkedHashSet<>();
        for (JsonNode f : body.path("features")) {
            JsonNode p = f.path("properties");
            JsonNode coords = f.path("geometry").path("coordinates");
            String nombre = displayName(p);
            if (nombre.isEmpty() || coords.size() < 2 || !vistos.add(nombre)) continue;
            out.add(new GeocodingResultDTO(nombre, coords.get(1).asDouble(), coords.get(0).asDouble(),
                    p.path("osm_value").asText(null)));
        }
        return out;
    }

    /** "Universidad de Antioquia, Calle 67 53-108, La Candelaria, Medellín". */
    static String displayName(JsonNode p) {
        Set<String> partes = new LinkedHashSet<>();
        add(partes, p.path("name").asText(""));
        String calle = p.path("street").asText("");
        String numero = p.path("housenumber").asText("");
        add(partes, numero.isEmpty() ? calle : (calle + " " + numero).trim());
        add(partes, p.path("district").asText(""));
        add(partes, p.path("city").asText(""));
        return String.join(", ", partes);
    }

    private static void add(Set<String> partes, String s) {
        if (!s.isBlank()) partes.add(s.trim());
    }
}
