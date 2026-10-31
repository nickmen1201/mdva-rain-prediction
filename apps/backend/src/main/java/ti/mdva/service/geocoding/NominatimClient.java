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
import java.text.Normalizer;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Cliente de Nominatim (OSM) que cumple su política de uso
 * (https://operations.osmfoundation.org/policies/nominatim/): User-Agent identificable,
 * como máximo 1 consulta por segundo en todo el Backend y caché de resultados. No sirve
 * autocompletado por tecla: el Frontend busca al enviar el texto (spec 008).
 */
@Slf4j
@Component
public class NominatimClient {

    /** Valle de Aburrá: lon mín, lat máx, lon máx, lat mín. */
    static final String VIEWBOX = "-75.72,6.55,-75.30,6.00";
    static final Duration TTL = Duration.ofHours(24);
    static final Duration MIN_INTERVAL = Duration.ofSeconds(1);
    static final int MAX_CACHE = 1_000;
    static final int LIMIT = 5;

    /** Espera bloqueante inyectable para probar el limitador sin dormir. */
    interface Sleeper {
        void sleep(Duration d) throws InterruptedException;
    }

    private record Cached<T>(T value, Instant expiresAt) {}

    private final RestTemplate restTemplate;
    private final String baseUrl;
    private final String userAgent;
    private final Clock clock;
    private final Sleeper sleeper;
    private final Map<String, Cached<List<GeocodingResultDTO>>> searchCache = new ConcurrentHashMap<>();
    private final Map<String, Cached<Optional<GeocodingResultDTO>>> reverseCache = new ConcurrentHashMap<>();
    private Instant lastCall = Instant.EPOCH;

    @Autowired
    public NominatimClient(RestTemplateBuilder builder,
                           @Value("${geocoding.nominatim.url}") String baseUrl,
                           @Value("${geocoding.nominatim.user-agent}") String userAgent) {
        this(builder.connectTimeout(Duration.ofSeconds(5)).readTimeout(Duration.ofSeconds(10)).build(),
                baseUrl, userAgent, Clock.systemUTC(), d -> Thread.sleep(d.toMillis()));
    }

    NominatimClient(RestTemplate restTemplate, String baseUrl, String userAgent, Clock clock, Sleeper sleeper) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.userAgent = userAgent;
        this.clock = clock;
        this.sleeper = sleeper;
    }

    /** Hasta 5 lugares del Valle de Aburrá que coinciden con el texto. */
    public List<GeocodingResultDTO> search(String query) {
        String key = normalize(query);
        if (key.length() < 3) {
            throw new IllegalArgumentException("La búsqueda debe tener al menos 3 caracteres.");
        }
        return cached(searchCache, key, () -> {
            URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/search")
                    .queryParam("q", query.trim())
                    .queryParam("format", "jsonv2")
                    .queryParam("limit", LIMIT)
                    .queryParam("countrycodes", "co")
                    .queryParam("viewbox", VIEWBOX)
                    .queryParam("bounded", 1)
                    .queryParam("accept-language", "es")
                    .encode().build().toUri();
            List<GeocodingResultDTO> out = new ArrayList<>();
            for (JsonNode n : call(uri)) out.add(toResult(n));
            return out;
        });
    }

    /** Dirección legible de un punto, o vacío si Nominatim no encuentra ninguna. */
    public Optional<GeocodingResultDTO> reverse(double lat, double lng) {
        String key = "%.5f,%.5f".formatted(lat, lng);
        return cached(reverseCache, key, () -> {
            URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/reverse")
                    .queryParam("lat", lat)
                    .queryParam("lon", lng)
                    .queryParam("format", "jsonv2")
                    .queryParam("accept-language", "es")
                    .encode().build().toUri();
            JsonNode n = call(uri);
            return n.has("error") ? Optional.empty() : Optional.of(toResult(n));
        });
    }

    private <T> T cached(Map<String, Cached<T>> cache, String key, java.util.function.Supplier<T> loader) {
        Instant now = clock.instant();
        Cached<T> hit = cache.get(key);
        if (hit != null && now.isBefore(hit.expiresAt())) return hit.value();
        T value = loader.get();
        if (cache.size() >= MAX_CACHE) cache.values().removeIf(c -> !clock.instant().isBefore(c.expiresAt()));
        if (cache.size() < MAX_CACHE) cache.put(key, new Cached<>(value, clock.instant().plus(TTL)));
        return value;
    }

    /** Una consulta a la vez y al menos 1 s desde la anterior (límite global de la política). */
    private synchronized JsonNode call(URI uri) {
        Duration wait = Duration.between(clock.instant(), lastCall.plus(MIN_INTERVAL));
        try {
            if (!wait.isNegative() && !wait.isZero()) sleeper.sleep(wait);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new GeocodingUnavailableException("Búsqueda interrumpida", e);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.set(HttpHeaders.USER_AGENT, userAgent);
        try {
            JsonNode body = restTemplate.exchange(uri, HttpMethod.GET, new HttpEntity<>(headers), JsonNode.class)
                    .getBody();
            if (body == null) throw new GeocodingUnavailableException("Nominatim respondió vacío", null);
            return body;
        } catch (RestClientException e) {
            log.warn("Nominatim falló para {}: {}", uri.getPath(), e.getMessage());
            throw new GeocodingUnavailableException("Nominatim no respondió", e);
        } finally {
            lastCall = clock.instant();
        }
    }

    private static GeocodingResultDTO toResult(JsonNode n) {
        return new GeocodingResultDTO(
                n.path("display_name").asText(),
                n.path("lat").asDouble(),
                n.path("lon").asDouble(),
                n.path("type").asText(null));
    }

    /** Minúsculas, sin tildes y con espacios colapsados: "  Parque  Explorá" → "parque explora". */
    static String normalize(String q) {
        if (q == null) return "";
        String sinTildes = Normalizer.normalize(q, Normalizer.Form.NFD).replaceAll("\\p{M}", "");
        return sinTildes.toLowerCase(Locale.ROOT).trim().replaceAll("\\s+", " ");
    }
}
