package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * Predicción horaria de lluvia para un punto específico.
 * Cada instancia representa UNA hora futura.
 *
 * Pipeline de datos:
 *   - Variables meteorológicas: Open-Meteo /forecast?hourly=...
 *   - Probabilidad de lluvia: modelo ML local (random_forest) usando esas variables
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HourlyForecastDTO {

    /** Timestamp de la hora pronosticada (zona local) */
    private OffsetDateTime timestamp;

    /** Hora del día 0-23 (atajo de UI) */
    private Integer hora;

    /** Probabilidad de lluvia del modelo random_forest [0.0–1.0] */
    private Double probabilidadRf;

    /** Variables meteorológicas usadas (para transparencia) */
    private Double temperaturaC;
    private Double humedadPct;
    private Double coberturaAnubosaPct;
    private Double velocidadVientoMs;
}
