package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for Municipality (Municipio).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MunicipalityDTO {
    private String id;
    private String name;
}
