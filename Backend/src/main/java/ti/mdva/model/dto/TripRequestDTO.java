package ti.mdva.model.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Request DTO para planificar un nuevo viaje.
 * Reemplaza el uso de idBarrioOrigen/idBarrioDestino por ubicaciones reales.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TripRequestDTO {

    @NotNull(message = "El ID del usuario es obligatorio")
    private Integer idUsuario;

    private String idVehiculo;

    /** Ubicación de origen con coordenadas o placeId de Google Places */
    @Valid
    @NotNull(message = "El origen es obligatorio")
    private LocationPointDTO origen;

    /** Ubicación de destino con coordenadas o placeId de Google Places */
    @Valid
    @NotNull(message = "El destino es obligatorio")
    private LocationPointDTO destino;
}
