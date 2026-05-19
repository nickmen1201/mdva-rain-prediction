package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.OffsetDateTime;

/**
 * DTO de una parada intermedia de un viaje multi-destino (Sprint 5.3).
 * Representa una fila de paradas_viaje (V5 + V6).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ParadaDTO {

    private Integer idParada;

    /** Orden de la parada en el viaje (1 = primera intermedia tras origen). */
    private Integer orden;

    private Double lat;
    private Double lng;
    private String nombre;

    /** Distancia en metros desde esta parada hasta la siguiente (o destino). Puede ser null. */
    private Integer distanciaAlSiguiente;

    /** Tiempo estimado en segundos hasta la siguiente parada (o destino). Puede ser null. */
    private Integer tiempoAlSiguiente;

    /** True si el conductor ya pasó por esta parada (V6). */
    private Boolean finalizado;

    /** Timestamp de cuando se marcó como finalizada (V6). Null si todavía no. */
    private OffsetDateTime horaLlegadaReal;
}
