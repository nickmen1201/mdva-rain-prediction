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
 *  - Un resultado de /api/geocoding/search (Nominatim), que ya trae lat/lng
 *
 * Al menos uno de los dos grupos debe estar presente.
 * Si viene placeId, el backend lo geocodifica para obtener lat/lng.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LocationPointDTO {

    /** Identificador de lugar heredado; ya no se resuelve: lat/lng son obligatorios al planificar (spec 008) */
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
