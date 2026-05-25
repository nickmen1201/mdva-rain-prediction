package ti.mdva.model.dto;

import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.OffsetDateTime;

@Data
@Builder(toBuilder = true)
@NoArgsConstructor
@AllArgsConstructor
public class AlertaViajeDTO {
    private Integer idAlerta;
    private String tipoAlerta;
    private String nivelSeveridad;
    private String accionSugerida;
    private String mensaje;
    private String detalleRecomendacion;
    private Boolean datoConLatencia;
    private OffsetDateTime timestampGeneracion;
    /** True si el usuario ya leyó la alerta (acción PATCH .../leer). */
    private Boolean leida;
}
