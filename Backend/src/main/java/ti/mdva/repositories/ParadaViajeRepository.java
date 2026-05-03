package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.springframework.stereotype.Repository;

import ti.mdva.model.dto.LocationPointDTO;

import java.util.List;

import static org.jooq.impl.DSL.field;
import static org.jooq.impl.DSL.table;

/**
 * Repositorio para paradas_viaje.
 * Usa DSLContext directamente (tablas V5 pendientes de regeneración JOOQ).
 */
@Repository
public class ParadaViajeRepository {

    private final DSLContext dsl;

    public ParadaViajeRepository(DSLContext dsl) {
        this.dsl = dsl;
    }

    /**
     * Persiste la lista de paradas de un viaje.
     */
    public void saveAll(int idViaje, List<LocationPointDTO> paradas) {
        if (paradas == null || paradas.isEmpty()) return;

        for (int i = 0; i < paradas.size(); i++) {
            LocationPointDTO parada = paradas.get(i);
            dsl.insertInto(table("paradas_viaje"))
               .set(field("id_viaje"), idViaje)
               .set(field("orden"),    i + 1)
               .set(field("lat"),      parada.getLat())
               .set(field("lng"),      parada.getLng())
               .set(field("nombre"),   parada.getDisplayName())
               .execute();
        }
    }
}
