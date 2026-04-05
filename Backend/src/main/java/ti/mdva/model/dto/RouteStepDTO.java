package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Un paso individual de la ruta (instrucción de giro).
 * Mapeado desde el campo "steps" de Google Directions API.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RouteStepDTO {

    /** Instrucción en texto limpio (sin HTML) */
    private String instruccion;

    /** Distancia del tramo en metros */
    private Integer distanciaMetros;

    /** Duración del tramo en segundos */
    private Integer duracionSegundos;

    /** Coordenadas de inicio del tramo */
    private Double startLat;
    private Double startLng;

    /** Coordenadas de fin del tramo */
    private Double endLat;
    private Double endLng;
}
