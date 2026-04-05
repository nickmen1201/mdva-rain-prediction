package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * Respuesta de planificación de viaje.
 * Incluye datos de ruta (Google), predicción ML y ajuste de tiempo.
 *
 * toBuilder = true habilita response.toBuilder().idViaje(x).build()
 */
@Data
@Builder(toBuilder = true)
@NoArgsConstructor
@AllArgsConstructor
public class TripResponseDTO {

    // ── Viaje persistido ───────────────────────────────────────────────────────
    private Integer idViaje;
    private OffsetDateTime horaInicio;

    // ── Puntos de ruta ─────────────────────────────────────────────────────────
    private LocationPointDTO origen;
    private LocationPointDTO destino;

    // ── Datos de Google Directions ─────────────────────────────────────────────
    private Integer tiempoBaseMin;
    private Integer distanciaMetros;
    private String overviewPolyline;
    private List<RouteStepDTO> pasos;

    // ── Predicción ML + clima ──────────────────────────────────────────────────
    private RainPredictionDTO prediccionLluvia;

    // ── Tiempo ajustado ────────────────────────────────────────────────────────
    private Integer tiempoEstimadoMin;
    private Double factorAjuste;
    private Boolean sugerirRutaAlterna;
    private String razonRutaAlterna;

    // ── Alerta visual ──────────────────────────────────────────────────────────
    private AlertaNivel alertaNivel;
    private String alertaMensaje;

    public enum AlertaNivel {
        VERDE,
        AMARILLO,
        ROJO
    }
}