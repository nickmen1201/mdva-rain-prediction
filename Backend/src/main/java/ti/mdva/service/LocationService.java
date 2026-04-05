package ti.mdva.service;

import java.util.List;

import ti.mdva.model.dto.CommuneDTO;
import ti.mdva.model.dto.MunicipalityDTO;
import ti.mdva.model.dto.NeighborhoodDTO;

/**
 * Service interface for location operations.
 */
public interface LocationService {

    /**
     * Retrieves all municipalities.
     *
     * @return list of all municipalities
     */
    List<MunicipalityDTO> getAllMunicipalities();

    /**
     * Retrieves communes by municipality ID.
     *
     * @param municipalityId the municipality ID
     * @return list of communes in the municipality
     */
    List<CommuneDTO> getCommunesByMunicipality(String municipalityId);

    /**
     * Retrieves neighborhoods by commune ID.
     *
     * @param communeId the commune ID
     * @return list of neighborhoods in the commune
     */
    List<NeighborhoodDTO> getNeighborhoodsByCommune(String communeId);
}
