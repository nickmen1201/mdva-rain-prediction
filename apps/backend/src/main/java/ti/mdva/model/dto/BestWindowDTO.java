package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * Recomendación de mejor ventana horaria para salir en las próximas N horas.
 * Cubre la propuesta inicial: "Recomendaciones de horarios con menor probabilidad de lluvia".
 *
 * Si la ventana óptima ya empezó (mejorHora.hora == hora actual), `salirAhora=true`
 * y el frontend puede mostrar "Mejor momento: ahora mismo".
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class BestWindowDTO {

    /** True si la mejor opción es salir ya. */
    private Boolean salirAhora;

    /** Mejor hora encontrada en la ventana analizada (mínima probabilidad de lluvia). */
    private OffsetDateTime mejorHora;

    /** Probabilidad de lluvia en esa mejor hora (0.0–1.0). */
    private Double probabilidadMejor;

    /** Diferencia en horas desde ahora hasta la mejor hora. 0 = ahora. */
    private Integer horasDeEspera;

    /** Mensaje accionable en español (instructivo, no sugestivo — decisión Sprint 5). */
    private String mensaje;
}
