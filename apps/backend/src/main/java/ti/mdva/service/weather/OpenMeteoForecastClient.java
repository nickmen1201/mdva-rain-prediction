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
 *
 * <p>Contrato de features 1.1.0 (spec 012): cada hora lleva la ventana del <b>mismo</b> pronóstico
 * (t−2…t+2) y la ubicación pedida. Se pide también el día anterior ({@code past_days=1}) para que la
 * hora en curso tenga sus vecinos; una hora sin sus cuatro vecinos contiguos no se devuelve (no se
 * rellenan valores).
 */
@Component
public class OpenMeteoForecastClient {

    private static final Logger log = LoggerFactory.getLogger(OpenMeteoForecastClient.class);

    static final List<String> VARIABLES = List.of(
            "temperature_2m", "relative_humidity_2m", "dew_point_2m", "cloud_cover", "wind_speed_10m",
            "wind_direction_10m", "pressure_msl", "precipitation", "cape");

    private static final int CLOUD = VARIABLES.indexOf("cloud_cover");
    private static final int PRECIP = VARIABLES.indexOf("precipitation");
    private static final int CAPE = VARIABLES.indexOf("cape");

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

    /** Serie horaria (ayer, hoy y mañana en UTC; solo horas con ventana completa) para un punto. */
    public List<HourlyInputs> hourly(double lat, double lng) {
        return hourly(List.of(new double[]{lat, lng})).get(0);
    }

    /** Serie horaria para varios puntos en una sola llamada, en el mismo orden. */
    public List<List<HourlyInputs>> hourly(List<double[]> points) {
        String lats = points.stream().map(p -> String.format(Locale.US, "%.5f", p[0])).collect(Collectors.joining(","));
        String lngs = points.stream().map(p -> String.format(Locale.US, "%.5f", p[1])).collect(Collectors.joining(","));
        String url = baseUrl + "?latitude=" + lats + "&longitude=" + lngs
                + "&hourly=" + String.join(",", VARIABLES)
                + "&past_days=1&forecast_days=2&timezone=GMT&wind_speed_unit=ms&temperature_unit=celsius"
                + "&precipitation_unit=mm";

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
        List<List<HourlyInputs>> out = new ArrayList<>(points.size());
        for (int i = 0; i < points.size(); i++) {
            out.add(parse(ubicaciones.get(i), points.get(i)[0], points.get(i)[1]));
        }
        return out;
    }

    /** Desde la primera hora con inicio ≥ {@code desde}, hasta {@code cantidad} horas consecutivas. */
    public static List<HourlyInputs> from(List<HourlyInputs> serie, Instant desde, int cantidad) {
        return serie.stream().filter(h -> !h.timeUtc().isBefore(desde)).limit(cantidad).toList();
    }

    /** Valores crudos de una hora completa de la serie. */
    private record Hora(Instant t, double[] v) {}

    static List<HourlyInputs> parse(JsonNode ubicacion, double lat, double lng) {
        verificarUnidades(ubicacion.path("hourly_units"));
        JsonNode hourly = ubicacion.path("hourly");
        JsonNode tiempos = hourly.path("time");
        Map<Instant, Hora> horas = new LinkedHashMap<>();
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
            horas.put(t, new Hora(t, v));
        }

        List<HourlyInputs> serie = new ArrayList<>();
        for (Hora h : horas.values()) {
            Hora p2 = horas.get(h.t().minusSeconds(7200)), p1 = horas.get(h.t().minusSeconds(3600));
            Hora n1 = horas.get(h.t().plusSeconds(3600)), n2 = horas.get(h.t().plusSeconds(7200));
            if (p2 == null || p1 == null || n1 == null || n2 == null) continue;  // sin ventana completa
            double[] v = h.v();
            HourlyInputs.Window w = new HourlyInputs.Window(
                    p2.v()[PRECIP], p1.v()[PRECIP], n1.v()[PRECIP], n2.v()[PRECIP],
                    p1.v()[CLOUD], n1.v()[CLOUD], p1.v()[CAPE], n1.v()[CAPE]);
            serie.add(new HourlyInputs(h.t(), v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], w, lat, lng));
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
