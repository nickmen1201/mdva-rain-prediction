package ti.mdva.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for municipality data.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Municipality in the Aburra Valley")
public class MunicipalityDTO {

    @Schema(description = "Unique municipality identifier", example = "MED")
    private String id;

    @Schema(description = "Municipality name", example = "Medellin")
    private String name;
}
