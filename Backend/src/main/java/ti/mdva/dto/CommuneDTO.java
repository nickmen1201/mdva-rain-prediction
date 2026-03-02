package ti.mdva.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for commune data.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Commune within a municipality")
public class CommuneDTO {

    @Schema(description = "Unique commune identifier", example = "COM-01")
    private String id;

    @Schema(description = "Commune name", example = "Popular")
    private String name;

    @Schema(description = "Parent municipality identifier", example = "MED")
    private String municipalityId;
}
