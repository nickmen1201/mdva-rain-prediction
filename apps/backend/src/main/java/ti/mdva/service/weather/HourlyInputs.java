package ti.mdva.service.weather;

import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Entradas crudas del modelo de lluvia para una hora y un punto (contrato de features v1.0.0,
 * specs/004-feature-contract): instante UTC + 9 variables del pronóstico de Open-Meteo.
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
        double cape
) {

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
        return m;
    }
}
