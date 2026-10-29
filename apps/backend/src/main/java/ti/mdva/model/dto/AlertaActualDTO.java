package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * Estado climático actual sobre un viaje ya planificado (HU031).
 *
 * Recalcula la predicción ML y el nivel de alerta usando las coordenadas
 * de origen del viaje guardado. No vuelve a llamar a Google Directions
 * — la ruta no cambia, solo el clima y, por tanto, la alerta.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class AlertaActualDTO {

    private Integer idViaje;
    private OffsetDateTime calculadoEn;

    private TripResponseDTO.AlertaNivel alertaNivel;
    private String alertaMensaje;
    private Double factorAjuste;
    private Boolean sugerirRutaAlterna;
    private String razonRutaAlterna;

    private RainPredictionDTO prediccionLluvia;
}
