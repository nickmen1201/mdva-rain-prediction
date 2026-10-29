package ti.mdva.model.dto;

import java.time.OffsetDateTime;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Resultado de la predicción de lluvia del modelo ML.
 * Agrupa el resultado del modelo random_forest (mayor AUC) y la fuente climática.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RainPredictionDTO {

    /** Probabilidad ≥ 0.5 */
    private Boolean llueve;

    /** Probabilidad de lluvia del modelo rain_classifier (ML API v2); conserva el nombre por compatibilidad */
    private Double probabilidadRf;

    /** Ya no se calcula (el modelo v2 no tiene segundo clasificador); siempre null */
    private Double probabilidadRl;

    /** Temperatura actual en °C (de Open-Meteo) */
    private Double temperaturaC;

    /** Humedad relativa % (de Open-Meteo) */
    private Double humedadPct;

    /** Cobertura nubosa % (de Open-Meteo) */
    private Double coberturaAnubosaPct;

    /** Velocidad del viento m/s (de Open-Meteo) */
    private Double velocidadVientoMs;
    /** Instante UTC de la hora del pronóstico usada (spec 007) */
    private OffsetDateTime timestampDatoUtc;
}
