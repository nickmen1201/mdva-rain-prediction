package ti.mdva.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for Neighborhood (Barrio).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class NeighborhoodDTO {
    private String id;
    private String name;
    private String communeId;
}
