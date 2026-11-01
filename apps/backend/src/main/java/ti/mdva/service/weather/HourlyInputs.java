package ti.mdva.service.weather;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Entradas crudas del modelo de lluvia para una hora y un punto (contrato de features v1.1.0,
 * specs/012-ml-depth/contracts/features.v1.1.md): instante UTC + 9 variables del pronóstico de
 * Open-Meteo para esa hora + la ventana del mismo pronóstico (horas vecinas) + la ubicación.
 */
public record HourlyInputs(
        Instant timeUtc,
        double temperature2m,
        double relativeHumidity2m,
        double dewPoint2m,
        double cloudCover,
        double windSpeed10m,
        double windDirection10m,
        double pressureMsl,
        double precipitation,
        double cape,
        Window window,
        double latitude,
        double longitude
) {

    /** Valores del mismo pronóstico en las horas vecinas (t−2…t+2). */
    public record Window(
            double precipitationPrev2,
            double precipitationPrev1,
            double precipitationNext1,
            double precipitationNext2,
            double cloudCoverPrev1,
            double cloudCoverNext1,
            double capePrev1,
            double capeNext1
    ) {}

    /** Registro con los nombres del contrato, listo para el ML API v2. */
    public Map<String, Object> toModelRecord() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("time_utc", timeUtc.toString());
        m.put("temperature_2m", temperature2m);
        m.put("relative_humidity_2m", relativeHumidity2m);
        m.put("dew_point_2m", dewPoint2m);
        m.put("cloud_cover", cloudCover);
        m.put("wind_speed_10m", windSpeed10m);
        m.put("wind_direction_10m", windDirection10m);
        m.put("pressure_msl", pressureMsl);
        m.put("precipitation", precipitation);
        m.put("cape", cape);
        m.put("precipitation_prev2", window.precipitationPrev2());
        m.put("precipitation_prev1", window.precipitationPrev1());
        m.put("precipitation_next1", window.precipitationNext1());
        m.put("precipitation_next2", window.precipitationNext2());
        m.put("cloud_cover_prev1", window.cloudCoverPrev1());
        m.put("cloud_cover_next1", window.cloudCoverNext1());
        m.put("cape_prev1", window.capePrev1());
        m.put("cape_next1", window.capeNext1());
        m.put("latitude", latitude);
        m.put("longitude", longitude);
        return m;
    }
}
