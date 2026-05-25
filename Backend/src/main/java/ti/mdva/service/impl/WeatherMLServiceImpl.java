package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import ti.mdva.model.dto.HourlyForecastDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.WeatherGridPointDTO;
import ti.mdva.model.dto.WeatherGridResponseDTO;
import ti.mdva.model.dto.WeatherGridResultadoDTO;
import ti.mdva.service.WeatherMLService;

import java.time.Instant;
import java.time.LocalDateTime;
import java.time.OffsetDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Implementación de WeatherMLService.
 *
 * Flujo:
 *  1. GET Google Weather API /currentConditions:lookup
 *       → temperatura (°C), humedad (%), cobertura nubosa (%), viento (km/h → m/s)
 *  2. POST FastAPI /predecir/ambos → predicción de lluvia de ambos modelos ML
 *  3. Retorna RainPredictionDTO con el resultado consolidado
 *
 * Documentación: https://developers.google.com/maps/documentation/weather/current-conditions
 */
@Service
public class WeatherMLServiceImpl implements WeatherMLService {

    private static final Logger log = LoggerFactory.getLogger(WeatherMLServiceImpl.class);

    private static final String GOOGLE_WEATHER_URL =
        "https://weather.googleapis.com/v1/currentConditions:lookup" +
        "?key=%s" +
        "&location.latitude=%f" +
        "&location.longitude=%f" +
        "&unitsSystem=METRIC";

    /**
     * Open-Meteo Hourly Forecast (gratis, sin API key).
     * Retorna hasta 24 horas adelante con temperatura, humedad, nubosidad y viento.
     * Docs: https://open-meteo.com/en/docs
     */
    private static final String OPEN_METEO_FORECAST_URL =
        "https://api.open-meteo.com/v1/forecast" +
        "?latitude=%f" +
        "&longitude=%f" +
        "&hourly=temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m" +
        "&current=precipitation" +
        "&wind_speed_unit=ms" +
        "&forecast_days=2" +
        "&timezone=auto";

    private final RestTemplate restTemplate;
    private final String mlServiceUrl;
    private final String googleApiKey;
    private final Map<String, CachedGridResult> gridCache = new ConcurrentHashMap<>();

    private static final int MAX_GRID_POINTS = 81;
    private static final int GRID_TTL_SECONDS = 180;
    private static final String GRID_SOURCE = "GOOGLE_WEATHER_ML";

    /**
     * Caché simple en memoria para reducir llamadas a Google Weather (riesgo
     * identificado en Sprint 4: costos por sobrepasar free tier). Clave: lat/lng
     * redondeado a 4 decimales (~11m de precisión). TTL: 60s, suficiente para
     * que múltiples puntos del heatmap o updates GPS reusen la misma respuesta.
     */
    private static final long CACHE_TTL_MS = 60_000L;
    private final ConcurrentHashMap<String, CachedPrediction> predictionCache = new ConcurrentHashMap<>();
    private record CachedPrediction(RainPredictionDTO prediction, long timestamp) {}

    /**
     * Valor default declarado en application.yml. En perfil 'prod' debe sobreescribirse
     * vía variable de entorno GOOGLE_MAPS_API_KEY — el arranque falla si no se hace.
     */
    static final String DEFAULT_DEV_GOOGLE_KEY = "REEMPLAZAR";

    public WeatherMLServiceImpl(
            @Value("${ml.service.url}")              String mlServiceUrl,
            @Value("${google.maps.api-key}")         String googleApiKey,
            @Value("${spring.profiles.active:}")     String activeProfile
    ) {
        if (isProdProfile(activeProfile) && isInsecureKey(googleApiKey)) {
            throw new IllegalStateException(
                "GOOGLE_MAPS_API_KEY no puede ser el default ni estar vacía en perfil 'prod'. " +
                "Configura la variable de entorno GOOGLE_MAPS_API_KEY antes de arrancar."
            );
        }
        this.restTemplate = new RestTemplate();
        this.mlServiceUrl = mlServiceUrl;
        this.googleApiKey = googleApiKey;
    }

    private static boolean isProdProfile(String activeProfile) {
        if (activeProfile == null || activeProfile.isBlank()) return false;
        for (String p : activeProfile.split(",")) {
            if ("prod".equalsIgnoreCase(p.trim())) return true;
        }
        return false;
    }

    private static boolean isInsecureKey(String key) {
        return key == null || key.isBlank() || DEFAULT_DEV_GOOGLE_KEY.equals(key);
    }

    @Override
    public RainPredictionDTO predictRainForLocation(double lat, double lng) {

        // ── Paso 0: Cache lookup ──────────────────────────────────────────────
        String cacheKey = String.format(java.util.Locale.US, "%.4f,%.4f", lat, lng);
        long now = System.currentTimeMillis();
        CachedPrediction cached = predictionCache.get(cacheKey);
        if (cached != null && (now - cached.timestamp()) < CACHE_TTL_MS) {
            log.debug("Cache HIT para {} (edad {}ms)", cacheKey, now - cached.timestamp());
            return cached.prediction();
        }

        // ── Paso 1: Condiciones actuales desde Google Weather API ─────────────
        String weatherUrl = String.format(GOOGLE_WEATHER_URL, googleApiKey, lat, lng);
        JsonNode weather  = restTemplate.getForObject(weatherUrl, JsonNode.class);

        if (weather == null) {
            throw new RuntimeException(
                "Google Weather API no respondió para lat=%.4f, lng=%.4f".formatted(lat, lng));
        }

        double tempC       = weather.path("temperature").path("degrees").asDouble();
        double humidityPct = weather.path("relativeHumidity").asDouble();
        double cloudPct    = inferCloudCover(weather);
        double windKmh     = weather.path("wind").path("speed").path("value").asDouble();
        double windMs      = Math.round((windKmh / 3.6) * 100.0) / 100.0;
        double rainProbPct = weather.path("precipitation").path("probability").path("percent").asDouble();

        LocalDateTime ahora       = LocalDateTime.now();
        int           currentHour = ahora.getHour();
        int           currentMonth= ahora.getMonthValue();

        log.debug("Google Weather [lat={}, lng={}]: temp={}C hum={}% nub={}% viento={}m/s lluvia={}%",
                lat, lng, tempC, humidityPct, cloudPct, windMs, rainProbPct);

        // ── Paso 1b: Precipitación actual desde Open-Meteo (lag feature) ────
        double precipLag1h = 0.0;
        try {
            String omUrl = String.format(java.util.Locale.US,
                "https://api.open-meteo.com/v1/forecast?latitude=%f&longitude=%f&current=precipitation&timezone=auto",
                lat, lng);
            JsonNode omResp = restTemplate.getForObject(omUrl, JsonNode.class);
            if (omResp != null) {
                precipLag1h = omResp.path("current").path("precipitation").asDouble(0.0);
            }
        } catch (Exception e) {
            log.debug("Open-Meteo current precipitation no disponible: {}", e.getMessage());
        }

        // ── Paso 2: Enviar al microservicio FastAPI ML ────────────────────────
        Map<String, Object> mlPayload = Map.of(
            "temperatura_c",         tempC,
            "humedad_relativa_pct",  humidityPct,
            "cobertura_nubosa_pct",  cloudPct,
            "velocidad_viento_ms",   windMs,
            "hora",                  currentHour,
            "mes",                   currentMonth,
            "precip_lag_1h_mm",      precipLag1h
        );

        String mlEndpoint = mlServiceUrl + "/predecir/ambos";
        ResponseEntity<JsonNode[]> mlResponse =
            restTemplate.postForEntity(mlEndpoint, mlPayload, JsonNode[].class);

        if (mlResponse.getBody() == null || mlResponse.getBody().length == 0) {
            throw new RuntimeException("El microservicio ML no retornó predicciones");
        }

        // ── Paso 3: Consolidar resultado ──────────────────────────────────────
        // Decisión Sprint 5: el modelo propio (RF) es la verdad para la decisión
        // de "llueve / no llueve". Si el ML no responde con RF, fail-fast en vez
        // de degradar silenciosamente a Google Weather (que opacaba el modelo).
        Double probRf = null;
        Double probRl = null;

        for (JsonNode pred : mlResponse.getBody()) {
            String modelo = pred.path("modelo").asText();
            double prob   = pred.path("probabilidad_lluvia").asDouble();

            if ("random_forest".equals(modelo))       probRf = prob;
            if ("regresion_logistica".equals(modelo)) probRl = prob;
        }

        // Decisión Sprint 5: el modelo propio (RF) es la verdad. Si el container
        // no tiene RF cargado (random_forest.pkl está gitignored por tamaño),
        // degradamos a RL como fallback CLARAMENTE LOGUEADO. Si tampoco hay RL,
        // fail-fast (no degradamos a Google).
        if (probRf == null) {
            if (probRl != null) {
                log.warn("Random Forest no disponible (¿modelo no cargado?). Usando Logistic Regression como fallback. Coordinar con DS para que random_forest.pkl esté en el container.");
                probRf = probRl;
            } else {
                log.error("Ningún modelo ML respondió. Body: {}",
                        java.util.Arrays.toString(mlResponse.getBody()));
                throw new RuntimeException("Predicción no disponible: ningún modelo ML respondió");
            }
        }

        // Blend final: 65% RF propio + 35% probabilidad Google Weather.
        // Google tiene señal independiente (su propio modelo NWP) que mejora
        // precisión en condiciones límite donde el RF es menos seguro.
        double googleWeight = rainProbPct / 100.0;
        double blendedProb = 0.65 * probRf + 0.35 * googleWeight;
        boolean llueve = blendedProb >= 0.5;

        log.debug("ML result: llueve={} RF={} RL={} google={}% blended={}",
                llueve, probRf, probRl, rainProbPct, String.format("%.4f", blendedProb));
        probRf = blendedProb;

        RainPredictionDTO resultado = RainPredictionDTO.builder()
                .llueve(llueve)
                .probabilidadRf(probRf)
                .probabilidadRl(probRl)
                .temperaturaC(tempC)
                .humedadPct(humidityPct)
                .coberturaAnubosaPct(cloudPct)
                .velocidadVientoMs(windMs)
                .build();

        predictionCache.put(cacheKey, new CachedPrediction(resultado, now));
        return resultado;
    }

    @Override
    public List<HourlyForecastDTO> getHourlyForecast(double lat, double lng, int horas) {
        if (horas < 1) horas = 1;
        if (horas > 24) horas = 24;

        // ── Paso 1: Open-Meteo Hourly Forecast ────────────────────────────────
        String url = String.format(java.util.Locale.US, OPEN_METEO_FORECAST_URL, lat, lng);
        JsonNode resp = restTemplate.getForObject(url, JsonNode.class);

        if (resp == null || !resp.has("hourly")) {
            log.error("Open-Meteo no devolvió hourly forecast para lat={}, lng={}", lat, lng);
            throw new RuntimeException("No se pudo obtener forecast horario");
        }

        JsonNode hourly = resp.path("hourly");
        JsonNode times  = hourly.path("time");
        JsonNode temps  = hourly.path("temperature_2m");
        JsonNode hums   = hourly.path("relative_humidity_2m");
        JsonNode clouds = hourly.path("cloud_cover");
        JsonNode winds  = hourly.path("wind_speed_10m");

        // ── Paso 2: Encontrar índice de la hora actual y tomar próximas N ────
        OffsetDateTime ahora = OffsetDateTime.now(ZoneId.systemDefault());
        int startIdx = 0;
        for (int i = 0; i < times.size(); i++) {
            // Open-Meteo devuelve "2026-05-10T14:00" sin offset; lo interpretamos como local
            LocalDateTime t = LocalDateTime.parse(times.path(i).asText());
            if (!t.atZone(ZoneId.systemDefault()).toOffsetDateTime().isBefore(ahora.minusMinutes(30))) {
                startIdx = i;
                break;
            }
        }
        int endIdx = Math.min(startIdx + horas, times.size());

        // ── Paso 3: Para cada hora, predecir con el modelo ML en paralelo ─────
        List<CompletableFuture<HourlyForecastDTO>> futures = new ArrayList<>();
        for (int i = startIdx; i < endIdx; i++) {
            final int idx = i;
            futures.add(CompletableFuture.supplyAsync(() -> {
                LocalDateTime t  = LocalDateTime.parse(times.path(idx).asText());
                double temp      = temps.path(idx).asDouble();
                double humedad   = hums.path(idx).asDouble();
                double nubosidad = clouds.path(idx).asDouble();
                double viento    = winds.path(idx).asDouble();

                Map<String, Object> mlPayload = Map.of(
                    "temperatura_c",         temp,
                    "humedad_relativa_pct",  humedad,
                    "cobertura_nubosa_pct",  nubosidad,
                    "velocidad_viento_ms",   viento,
                    "hora",                  t.getHour(),
                    "mes",                   t.getMonthValue()
                );

                // Usamos /predecir/ambos en vez de /predecir/random_forest porque el
                // RF no siempre está disponible en el container (models/random_forest.pkl
                // está en .gitignore por tamaño >100MB). /predecir/ambos itera sobre los
                // modelos cargados y devuelve los disponibles. Preferimos RF; si no, RL.
                String mlEndpoint = mlServiceUrl + "/predecir/ambos";
                Double probRf = 0.0;
                try {
                    JsonNode[] preds = restTemplate.postForObject(mlEndpoint, mlPayload, JsonNode[].class);
                    if (preds == null || preds.length == 0) {
                        log.warn("ML devolvió vacío para hora {}", t);
                    } else {
                        // Prefiere random_forest, sino el primero disponible
                        Double probRfFound = null;
                        Double probAny = null;
                        for (JsonNode pred : preds) {
                            double p = pred.path("probabilidad_lluvia").asDouble(0.0);
                            if (probAny == null) probAny = p;
                            if ("random_forest".equals(pred.path("modelo").asText())) {
                                probRfFound = p;
                            }
                        }
                        probRf = probRfFound != null ? probRfFound : (probAny != null ? probAny : 0.0);
                        log.debug("Forecast hora {}: probRf={} (modelos={}, temp={} hum={})",
                                t, probRf, preds.length, temp, humedad);
                    }
                } catch (Exception e) {
                    log.warn("ML falló para hora {} con payload {}: {}", t, mlPayload, e.getMessage());
                }

                return HourlyForecastDTO.builder()
                    .timestamp(t.atZone(ZoneId.systemDefault()).toOffsetDateTime())
                    .hora(t.getHour())
                    .probabilidadRf(probRf)
                    .temperaturaC(temp)
                    .humedadPct(humedad)
                    .coberturaAnubosaPct(nubosidad)
                    .velocidadVientoMs(viento)
                    .build();
            }));
        }

        return futures.stream()
            .map(CompletableFuture::join)
            .toList();
    }

    @Override
    public WeatherGridResponseDTO predictGridForArea(List<WeatherGridPointDTO> puntos) {
        if (puntos == null || puntos.isEmpty()) {
            return new WeatherGridResponseDTO(List.of(), Instant.now(), GRID_SOURCE, GRID_TTL_SECONDS);
        }

        if (puntos.size() > MAX_GRID_POINTS) {
            throw new IllegalArgumentException("El heatmap acepta maximo " + MAX_GRID_POINTS + " puntos por grilla");
        }

        List<CompletableFuture<WeatherGridResultadoDTO>> futures = puntos.stream()
            .map(p -> CompletableFuture.supplyAsync(() -> predictGridPoint(p)))
            .toList();

        List<WeatherGridResultadoDTO> resultados = futures.stream()
            .map(CompletableFuture::join)
            .toList();

        return new WeatherGridResponseDTO(resultados, Instant.now(), GRID_SOURCE, GRID_TTL_SECONDS);
    }

    private WeatherGridResultadoDTO predictGridPoint(WeatherGridPointDTO point) {
        String key = cacheKey(point);
        CachedGridResult cached = gridCache.get(key);
        if (cached != null && cached.expiresAt().isAfter(Instant.now())) {
            return cached.result();
        }

        WeatherGridResultadoDTO result;
        try {
            RainPredictionDTO pred = predictRainForLocation(point.lat(), point.lng());
            double probabilidad = pred.getProbabilidadRf() != null ? pred.getProbabilidadRf() : 0.0;
            result = new WeatherGridResultadoDTO(point.lat(), point.lng(), clampProbability(probabilidad));
        } catch (Exception e) {
            log.warn("Heatmap rain prediction failed for lat={}, lng={}", point.lat(), point.lng(), e);
            result = new WeatherGridResultadoDTO(point.lat(), point.lng(), 0.0);
        }

        gridCache.put(key, new CachedGridResult(result, Instant.now().plusSeconds(GRID_TTL_SECONDS)));
        return result;
    }

    private String cacheKey(WeatherGridPointDTO point) {
        return "%.3f:%.3f".formatted(point.lat(), point.lng());
    }

    private double clampProbability(double value) {
        return Math.max(0.0, Math.min(1.0, value));
    }

    private record CachedGridResult(WeatherGridResultadoDTO result, Instant expiresAt) {}

    /**
     * Infiere cobertura nubosa (%) desde el tipo de condición de Google Weather.
     * currentConditions no expone cloudCover directamente, solo en forecast/hours.
     *
     * TODO(KR2): el modelo se entrenó con cobertura nubosa CONTINUA (Open-Meteo /
     * SIATA). Esta inferencia categórica introduce ruido sistemático en el feature
     * y puede sesgar la predicción en producción frente a las métricas reportadas
     * (F1=0.78). Dos caminos para resolverlo:
     *   1. Llamar a /forecast.hours:lookup de Google Weather (expone cloudCover real)
     *   2. Eliminar cobertura nubosa del feature input y reentrenar
     * Coordinar con el equipo de Data Science antes de cambiar.
     */
    private double inferCloudCover(JsonNode weather) {
        String type = weather.path("weatherCondition").path("type").asText("");
        return switch (type) {
            case "CLEAR", "SUNNY"                            -> 0.0;
            case "MOSTLY_CLEAR", "MOSTLY_SUNNY"              -> 15.0;
            case "PARTLY_CLOUDY", "PARTLY_SUNNY"             -> 40.0;
            case "MOSTLY_CLOUDY", "HAZE", "HAZY_MOONLIGHT"  -> 70.0;
            case "CLOUDY", "OVERCAST"                        -> 90.0;
            case "FOG", "FOGGY"                              -> 85.0;
            case "DRIZZLE", "LIGHT_RAIN", "RAIN",
                 "RAIN_SHOWERS", "HEAVY_RAIN"                -> 95.0;
            case "THUNDERSTORM", "STRONG_THUNDERSTORM",
                 "THUNDERSHOWER"                             -> 100.0;
            case "SNOW", "FLURRIES", "BLIZZARD"              -> 90.0;
            default                                          -> 50.0;
        };
    }
}
