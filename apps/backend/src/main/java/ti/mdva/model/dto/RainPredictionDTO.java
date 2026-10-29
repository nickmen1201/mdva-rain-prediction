package ti.mdva.model.dto;

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

    /** Si alguno de los modelos predice lluvia */
    private Boolean llueve;

    /** Probabilidad del modelo random_forest (mayor AUC: 0.82) */
    private Double probabilidadRf;

    /** Probabilidad del modelo regresión logística */
    private Double probabilidadRl;

    /** Temperatura actual en °C (de Open-Meteo) */
    private Double temperaturaC;

    /** Humedad relativa % (de Open-Meteo) */
    private Double humedadPct;

    /** Cobertura nubosa % (de Open-Meteo) */
    private Double coberturaAnubosaPct;

    /** Velocidad del viento m/s (de Open-Meteo) */
    private Double velocidadVientoMs;
}
