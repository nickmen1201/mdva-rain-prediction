package ti.mdva.model.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MonitoreoResponseDTO {
    private AlertaViajeDTO alertaNueva;
    private RainPredictionDTO condicionesActuales;
}
