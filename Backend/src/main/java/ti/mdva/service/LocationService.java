package ti.mdva.service;

import ti.mdva.dto.CommuneDTO;
import ti.mdva.dto.MunicipalityDTO;
import ti.mdva.dto.NeighborhoodDTO;

import java.util.List;

/**
 * Service interface for location management operations.
 *
 * @author MDVA Team
 * @version 1.0
 */
public interface LocationService {

    /**
     * Retrieves all municipalities.
     *
     * @return list of all municipalities
     */
    List<MunicipalityDTO> getAllMunicipalities();

    /**
     * Retrieves all communes belonging to a municipality.
     *
     * @param municipalityId the municipality identifier
     * @return list of communes
     */
    List<CommuneDTO> getCommunesByMunicipality(String municipalityId);

    /**
     * Retrieves all neighborhoods belonging to a commune.
     *
     * @param communeId the commune identifier
     * @return list of neighborhoods
     */
    List<NeighborhoodDTO> getNeighborhoodsByCommune(String communeId);
}
