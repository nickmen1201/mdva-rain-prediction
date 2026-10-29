package ti.mdva.service.weather;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.web.client.RestTemplateBuilder;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Pronóstico horario de Open-Meteo con las 9 variables del contrato de features, en UTC y
 * con unidades explícitas (las mismas que en el entrenamiento, specs/003 y specs/004).
 * Las unidades declaradas por la fuente se verifican: nunca se convierten en silencio.
 */
@Component
public class OpenMeteoForecastClient {

    private static final Logger log = LoggerFactory.getLogger(OpenMeteoForecastClient.class);

    static final List<String> VARIABLES = List.of(
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", "cloud_cover", "wind_speed_10m",
            "wind_direction_10m", "pressure_msl", "precipitation", "cape");

    static final Map<String, String> EXPECTED_UNITS = Map.of(
            "temperature_2m", "°C",
            "relative_humidity_2m", "%",
            "dew_point_2m", "°C",
            "cloud_cover", "%",
            "wind_speed_10m", "m/s",
            "wind_direction_10m", "°",
            "pressure_msl", "hPa",
            "precipitation", "mm",
            "cape", "J/kg");

    private final RestTemplate restTemplate;
    private final String baseUrl;

    @Autowired
    public OpenMeteoForecastClient(
            RestTemplateBuilder builder,
            @Value("${weather.open-meteo.url:https://api.open-meteo.com/v1/forecast}") String baseUrl) {
        this(builder.connectTimeout(Duration.ofSeconds(5)).readTimeout(Duration.ofSeconds(15)).build(), baseUrl);
    }

    OpenMeteoForecastClient(RestTemplate restTemplate, String baseUrl) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
    }

    /** Serie horaria (hoy y mañana, UTC) para un punto. */
    public List<HourlyInputs> hourly(double lat, double lng) {
        return hourly(List.of(new double[]{lat, lng})).get(0);
    }

    /** Serie horaria para varios puntos en una sola llamada, en el mismo orden. */
    public List<List<HourlyInputs>> hourly(List<double[]> points) {
        String lats = points.stream().map(p -> String.format(Locale.US, "%.5f", p[0])).collect(Collectors.joining(","));
        String lngs = points.stream().map(p -> String.format(Locale.US, "%.5f", p[1])).collect(Collectors.joining(","));
        String url = baseUrl + "?latitude=" + lats + "&longitude=" + lngs
                + "&hourly=" + String.join(",", VARIABLES)
                + "&forecast_days=2&timezone=GMT&wind_speed_unit=ms&temperature_unit=celsius&precipitation_unit=mm";

        JsonNode resp = restTemplate.getForObject(url, JsonNode.class);
        if (resp == null) {
            throw new IllegalStateException("Open-Meteo no respondió");
        }
        List<JsonNode> ubicaciones = new ArrayList<>();
        if (resp.isArray()) resp.forEach(ubicaciones::add); else ubicaciones.add(resp);
        if (ubicaciones.size() != points.size()) {
            throw new IllegalStateException(
                    "Open-Meteo devolvió %d ubicaciones; se pidieron %d".formatted(ubicaciones.size(), points.size()));
        }
        return ubicaciones.stream().map(OpenMeteoForecastClient::parse).toList();
    }

    /** Desde la primera hora con inicio ≥ {@code desde}, hasta {@code cantidad} horas consecutivas. */
    public static List<HourlyInputs> from(List<HourlyInputs> serie, Instant desde, int cantidad) {
        return serie.stream().filter(h -> !h.timeUtc().isBefore(desde)).limit(cantidad).toList();
    }

    static List<HourlyInputs> parse(JsonNode ubicacion) {
        verificarUnidades(ubicacion.path("hourly_units"));
        JsonNode hourly = ubicacion.path("hourly");
        JsonNode tiempos = hourly.path("time");
        List<HourlyInputs> serie = new ArrayList<>();
        for (int i = 0; i < tiempos.size(); i++) {
            double[] v = new double[VARIABLES.size()];
            boolean completa = true;
            for (int j = 0; j < VARIABLES.size(); j++) {
                JsonNode valor = hourly.path(VARIABLES.get(j)).path(i);
                if (valor.isMissingNode() || valor.isNull()) {
                    completa = false;
                    break;
                }
                v[j] = valor.asDouble();
            }
            Instant t = LocalDateTime.parse(tiempos.path(i).asText()).toInstant(ZoneOffset.UTC);
            if (!completa) {
                log.debug("Open-Meteo: hora {} incompleta; se omite (no se rellenan valores)", t);
                continue;
            }
            serie.add(new HourlyInputs(t, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8]));
        }
        return serie;
    }

    private static void verificarUnidades(JsonNode unidades) {
        Map<String, String> distintas = new LinkedHashMap<>();
        EXPECTED_UNITS.forEach((variable, esperada) -> {
            String recibida = unidades.path(variable).asText(null);
            if (!esperada.equals(recibida)) distintas.put(variable, recibida + " (esperado " + esperada + ")");
        });
        if (!distintas.isEmpty()) {
            throw new IllegalStateException("Open-Meteo declaró unidades inesperadas: " + distintas);
        }
    }
}
