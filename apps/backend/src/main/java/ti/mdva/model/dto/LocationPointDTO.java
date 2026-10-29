package ti.mdva.model.dto;

import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Representa un punto geográfico que puede venir de:
 *  - Coordenadas directas (lat/lng) seleccionadas en el mapa
 *  - Un placeId de Google Places (desde Autocomplete)
 *
 * Al menos uno de los dos grupos debe estar presente.
 * Si viene placeId, el backend lo geocodifica para obtener lat/lng.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LocationPointDTO {

    /** Google Places placeId (ej: "ChIJN1t_tDeuEmsRUsoyG83frY4") */
    private String placeId;

    /** Nombre legible del lugar (ej: "Aeropuerto José María Córdova") */
    private String displayName;

    @DecimalMin(value = "-90.0", message = "Latitud fuera de rango")
    @DecimalMax(value = "90.0",  message = "Latitud fuera de rango")
    private Double lat;

    @DecimalMin(value = "-180.0", message = "Longitud fuera de rango")
    @DecimalMax(value = "180.0",  message = "Longitud fuera de rango")
    private Double lng;
}
