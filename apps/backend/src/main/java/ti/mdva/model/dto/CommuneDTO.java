package ti.mdva.model.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Data Transfer Object for Commune (Comuna).
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class CommuneDTO {
    private String id;
    private String name;
    private String municipalityId;
}
