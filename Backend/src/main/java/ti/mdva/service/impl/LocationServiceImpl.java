package ti.mdva.service.impl;

import org.jooq.DSLContext;
import org.springframework.stereotype.Service;
import ti.mdva.dto.CommuneDTO;
import ti.mdva.dto.MunicipalityDTO;
import ti.mdva.dto.NeighborhoodDTO;
import ti.mdva.service.LocationService;

import java.util.List;

import static ti.mdva.jooq.Tables.*;

/**
 * Implementation of LocationService using JOOQ.
 */
@Service
public class LocationServiceImpl implements LocationService {

    private final DSLContext dsl;

    public LocationServiceImpl(DSLContext dsl) {
        this.dsl = dsl;
    }

    @Override
    public List<MunicipalityDTO> getAllMunicipalities() {
        return dsl.selectFrom(MUNICIPIOS)
                .fetch()
                .map(record -> MunicipalityDTO.builder()
                        .id(record.getIdMunicipio())
                        .name(record.getNombre())
                        .build());
    }

    @Override
    public List<CommuneDTO> getCommunesByMunicipality(String municipalityId) {
        return dsl.selectFrom(COMUNAS)
                .where(COMUNAS.ID_MUNICIPIO.eq(municipalityId))
                .fetch()
                .map(record -> CommuneDTO.builder()
                        .id(record.getIdComuna())
                        .name(record.getNombre())
                        .municipalityId(record.getIdMunicipio())
                        .build());
    }

    @Override
    public List<NeighborhoodDTO> getNeighborhoodsByCommune(String communeId) {
        return dsl.selectFrom(BARRIOS)
                .where(BARRIOS.ID_COMUNA.eq(communeId))
                .fetch()
                .map(record -> NeighborhoodDTO.builder()
                        .id(record.getIdBarrio())
                        .name(record.getNombre())
                        .communeId(record.getIdComuna())
                        .build());
    }
}
