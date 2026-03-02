package ti.mdva.service.impl;

import jakarta.persistence.EntityManager;
import jakarta.persistence.PersistenceContext;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import ti.mdva.dto.CommuneDTO;
import ti.mdva.dto.MunicipalityDTO;
import ti.mdva.dto.NeighborhoodDTO;
import ti.mdva.service.LocationService;

import java.util.List;

/**
 * Implementation of the LocationService interface.
 * <p>
 * Retrieves geographic data from the PostgreSQL database using JPA.
 * Provides access to the location hierarchy: Municipality -> Commune -> Neighborhood.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Slf4j
@Service
public class LocationServiceImpl implements LocationService {

    @PersistenceContext
    private EntityManager entityManager;

    /**
     * {@inheritDoc}
     */
    @Override
    @SuppressWarnings("unchecked")
    public List<MunicipalityDTO> getAllMunicipalities() {
        log.debug("Fetching all municipalities");

        String sql = "SELECT id_municipio, nombre FROM municipios ORDER BY nombre";

        List<Object[]> results = entityManager.createNativeQuery(sql).getResultList();

        return results.stream()
                .map(row -> MunicipalityDTO.builder()
                        .id((String) row[0])
                        .name((String) row[1])
                        .build())
                .toList();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @SuppressWarnings("unchecked")
    public List<CommuneDTO> getCommunesByMunicipality(String municipalityId) {
        log.debug("Fetching communes for municipality: {}", municipalityId);

        String sql = "SELECT id_comuna, nombre, id_municipio FROM comunas WHERE id_municipio = :municipalityId ORDER BY nombre";

        List<Object[]> results = entityManager.createNativeQuery(sql)
                .setParameter("municipalityId", municipalityId)
                .getResultList();

        return results.stream()
                .map(row -> CommuneDTO.builder()
                        .id((String) row[0])
                        .name((String) row[1])
                        .municipalityId((String) row[2])
                        .build())
                .toList();
    }

    /**
     * {@inheritDoc}
     */
    @Override
    @SuppressWarnings("unchecked")
    public List<NeighborhoodDTO> getNeighborhoodsByCommune(String communeId) {
        log.debug("Fetching neighborhoods for commune: {}", communeId);

        String sql = "SELECT id_barrio, nombre, id_comuna FROM barrios WHERE id_comuna = :communeId ORDER BY nombre";

        List<Object[]> results = entityManager.createNativeQuery(sql)
                .setParameter("communeId", communeId)
                .getResultList();

        return results.stream()
                .map(row -> NeighborhoodDTO.builder()
                        .id((String) row[0])
                        .name((String) row[1])
                        .communeId((String) row[2])
                        .build())
                .toList();
    }
}
