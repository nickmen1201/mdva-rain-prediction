package ti.mdva.service.impl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.model.dto.WeatherGridResultadoDTO;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.weather.HourlyInputs;
import ti.mdva.service.weather.MlApiV2Client;
import ti.mdva.service.weather.OpenMeteoForecastClient;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Implementación de WeatherMLService (specs/007-backend-weather-openmeteo).
 *
 * Flujo:
 *  1. Open-Meteo: pronóstico horario con las 9 variables del contrato de features, en UTC.
 *  2. ML API v2: probabilidad de lluvia (individual o por lotes) con el instante UTC del dato.
 *
 * Sin APIs de clima de pago, sin mezclas no evaluadas (H-21) y sin probabilidades inventadas
 * cuando algo falla (H-22).
 */
@Service
public class WeatherMLServiceImpl implements WeatherMLService {

    private static final Logger log = LoggerFactory.getLogger(WeatherMLServiceImpl.class);

    static final ZoneId BOGOTA = ZoneId.of("America/Bogota");
    private static final long CACHE_TTL_SECONDS = 180;
    private static final int MAX_GRID_POINTS = 81;
    private static final int GRID_TTL_SECONDS = 180;
    private static final String GRID_SOURCE = "OPEN_METEO_ML_V2";
    /** Probabilidad a partir de la cual la respuesta marca "llueve" (sin cambios respecto a la versión anterior). */
    private static final double UMBRAL_LLUEVE = 0.5;

    private final OpenMeteoForecastClient openMeteo;
    private final MlApiV2Client mlApi;
    private final Clock clock;

    private record Cached<T>(T value, Instant expiresAt) {}

    private final Map<String, Cached<List<HourlyInputs>>> seriesCache = new ConcurrentHashMap<>();
    private final Map<String, Cached<RainPredictionDTO>> predictionCache = new ConcurrentHashMap<>();
    private final Map<String, Cached<WeatherGridResultadoDTO>> gridCache = new ConcurrentHashMap<>();

    @Autowired
    public WeatherMLServiceImpl(OpenMeteoForecastClient openMeteo, MlApiV2Client mlApi) {
        this(openMeteo, mlApi, Clock.systemUTC());
    }

    WeatherMLServiceImpl(OpenMeteoForecastClient openMeteo, MlApiV2Client mlApi, Clock clock) {
        this.openMeteo = openMeteo;
        this.mlApi = mlApi;
        this.clock = clock;
    }

    @Override
    public RainPredictionDTO predictRainForLocation(double lat, double lng) {
        String key = key(lat, lng, "%.4f");
        Cached<RainPredictionDTO> cached = predictionCache.get(key);
        if (vigente(cached)) {
            return cached.value();
        }

        HourlyInputs actual = currentInputs(lat, lng);
        MlApiV2Client.Prediction pred = mlApi.predictBatch(List.of(actual)).get(0);

        RainPredictionDTO resultado = RainPredictionDTO.builder()
                .llueve(pred.probability() >= UMBRAL_LLUEVE)
                .probabilidadRf(pred.probability())
                .probabilidadRl(null) // el modelo v2 no tiene un segundo clasificador
                .temperaturaC(actual.temperature2m())
                .humedadPct(actual.relativeHumidity2m())
                .coberturaAnubosaPct(actual.cloudCover())
                .velocidadVientoMs(actual.windSpeed10m())
                .timestampDatoUtc(actual.timeUtc().atOffset(ZoneOffset.UTC))
                .build();

        predictionCache.put(key, new Cached<>(resultado, ahora().plusSeconds(CACHE_TTL_SECONDS)));
        return resultado;
    }

    @Override
    public HourlyInputs currentInputs(double lat, double lng) {
        Instant horaEnCurso = ahora().truncatedTo(ChronoUnit.HOURS);
        List<HourlyInputs> desde = OpenMeteoForecastClient.from(serie(lat, lng), horaEnCurso, 1);
        if (desde.isEmpty()) {
            throw new IllegalStateException("Open-Meteo no tiene la hora en curso para lat=%s, lng=%s".formatted(lat, lng));
        }
        HourlyInputs actual = desde.get(0);
        if (!actual.timeUtc().equals(horaEnCurso)) {
            log.warn("Open-Meteo sin la hora {}; se usa la siguiente disponible {}", horaEnCurso, actual.timeUtc());
        }
        return actual;
    }

    @Override
    public List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas) {
        int n = Math.max(1, Math.min(24, horas));
        // Igual que antes: la primera hora cuyo inicio no sea anterior a "ahora − 30 min"
        Instant desde = ahora().minus(30, ChronoUnit.MINUTES);
        List<HourlyInputs> seleccion = OpenMeteoForecastClient.from(serie(lat, lng), desde, n);
        List<MlApiV2Client.Prediction> preds = mlApi.predictBatch(seleccion);

        List<HourlyForecastDTO> out = new ArrayList<>(seleccion.size());
        for (int i = 0; i < seleccion.size(); i++) {
            HourlyInputs h = seleccion.get(i);
            out.add(HourlyForecastDTO.builder()
                    .timestamp(h.timeUtc().atOffset(ZoneOffset.UTC))
                    .hora(h.timeUtc().atZone(BOGOTA).getHour())
                    .probabilidadRf(preds.get(i).probability())
                    .temperaturaC(h.temperature2m())
                    .humedadPct(h.relativeHumidity2m())
                    .coberturaAnubosaPct(h.cloudCover())
                    .velocidadVientoMs(h.windSpeed10m())
                    .build());
        }
        return out;
    }

    @Override
    public WeatherGridResponseDTO predictGridForArea(List<WeatherGridPointDTO> puntos) {
        if (puntos == null || puntos.isEmpty()) {
            return new WeatherGridResponseDTO(List.of(), ahora(), GRID_SOURCE, GRID_TTL_SECONDS);
        }
        if (puntos.size() > MAX_GRID_POINTS) {
            throw new IllegalArgumentException("El heatmap acepta maximo " + MAX_GRID_POINTS + " puntos por grilla");
        }

        Map<String, WeatherGridResultadoDTO> resueltos = new HashMap<>();
        List<WeatherGridPointDTO> faltantes = new ArrayList<>();
        for (WeatherGridPointDTO p : puntos) {
            Cached<WeatherGridResultadoDTO> c = gridCache.get(key(p.lat(), p.lng(), "%.3f"));
            if (vigente(c)) resueltos.put(key(p.lat(), p.lng(), "%.3f"), c.value());
            else faltantes.add(p);
        }

        if (!faltantes.isEmpty()) {
            // Una consulta de clima y una de predicción para toda la grilla (SC-002); si falla, falla todo (H-22)
            Instant horaEnCurso = ahora().truncatedTo(ChronoUnit.HOURS);
            List<List<HourlyInputs>> series = openMeteo.hourly(
                    faltantes.stream().map(p -> new double[]{p.lat(), p.lng()}).toList());
            List<HourlyInputs> entradas = new ArrayList<>(faltantes.size());
            for (int i = 0; i < faltantes.size(); i++) {
                List<HourlyInputs> h = OpenMeteoForecastClient.from(series.get(i), horaEnCurso, 1);
                if (h.isEmpty()) {
                    throw new IllegalStateException("Open-Meteo sin la hora en curso para un punto de la grilla");
                }
                entradas.add(h.get(0));
            }
            List<MlApiV2Client.Prediction> preds = mlApi.predictBatch(entradas);
            Instant expira = ahora().plusSeconds(GRID_TTL_SECONDS);
            for (int i = 0; i < faltantes.size(); i++) {
                WeatherGridPointDTO p = faltantes.get(i);
                WeatherGridResultadoDTO r = new WeatherGridResultadoDTO(p.lat(), p.lng(), preds.get(i).probability());
                String k = key(p.lat(), p.lng(), "%.3f");
                gridCache.put(k, new Cached<>(r, expira));
                resueltos.put(k, r);
            }
        }

        List<WeatherGridResultadoDTO> resultados = puntos.stream()
                .map(p -> resueltos.get(key(p.lat(), p.lng(), "%.3f")))
                .toList();
        return new WeatherGridResponseDTO(resultados, ahora(), GRID_SOURCE, GRID_TTL_SECONDS);
    }

    private List<HourlyInputs> serie(double lat, double lng) {
        String key = key(lat, lng, "%.4f");
        Cached<List<HourlyInputs>> cached = seriesCache.get(key);
        if (vigente(cached)) {
            return cached.value();
        }
        List<HourlyInputs> serie = openMeteo.hourly(lat, lng);
        seriesCache.put(key, new Cached<>(serie, ahora().plusSeconds(CACHE_TTL_SECONDS)));
        return serie;
    }

    private boolean vigente(Cached<?> c) {
        return c != null && c.expiresAt().isAfter(ahora());
    }

    private Instant ahora() {
        return clock.instant();
    }

    private static String key(double lat, double lng, String formato) {
        return String.format(Locale.US, formato + "," + formato, lat, lng);
    }
}
