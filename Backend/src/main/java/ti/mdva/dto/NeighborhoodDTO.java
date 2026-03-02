package ti.mdva.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for neighborhood data.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Neighborhood within a commune")
public class NeighborhoodDTO {

    @Schema(description = "Unique neighborhood identifier", example = "BAR-001")
    private String id;

    @Schema(description = "Neighborhood name", example = "Santo Domingo Savio")
    private String name;

    @Schema(description = "Parent commune identifier", example = "COM-01")
    private String communeId;
}
