package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.jooq.Record;
import org.springframework.stereotype.Repository;

import ti.mdva.model.dto.LocationPointDTO;
import ti.mdva.model.dto.ParadaDTO;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.stream.Collectors;

import static org.jooq.impl.DSL.field;
import static org.jooq.impl.DSL.table;

/**
 * Repositorio para paradas_viaje (Sprint 5.3).
 * Usa DSLContext directamente porque V5+V6 están pendientes de regeneración JOOQ.
 */
@Repository
public class ParadaViajeRepository {

    private final DSLContext dsl;

    public ParadaViajeRepository(DSLContext dsl) {
        this.dsl = dsl;
    }

    /**
     * Persiste la lista de paradas de un viaje, asignando `orden` por su posición.
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

    /**
     * Lista las paradas de un viaje, ordenadas por `orden`.
     * Retorna lista vacía si el viaje no tiene paradas (viaje directo).
     */
    public List<ParadaDTO> findByViajeId(int idViaje) {
        return dsl.select(
                    field("id_parada", Integer.class),
                    field("orden", Integer.class),
                    field("lat", Double.class),
                    field("lng", Double.class),
                    field("nombre", String.class),
                    field("distancia_al_siguiente", Integer.class),
                    field("tiempo_al_siguiente", Integer.class),
                    field("finalizado", Boolean.class),
                    field("hora_llegada_real", OffsetDateTime.class)
                )
                .from(table("paradas_viaje"))
                .where(field("id_viaje", Integer.class).eq(idViaje))
                .orderBy(field("orden"))
                .fetch()
                .stream()
                .map(this::recordToDTO)
                .collect(Collectors.toList());
    }

    /**
     * Marca una parada como finalizada (V6). Idempotente: si ya estaba finalizada,
     * conserva la primera `hora_llegada_real` y no la sobrescribe.
     *
     * @return true si la parada existía y se actualizó (o ya estaba finalizada),
     *         false si no existe esa combinación viaje+orden
     */
    public boolean marcarParadaFinalizada(int idViaje, int orden) {
        int filas = dsl.update(table("paradas_viaje"))
            .set(field("finalizado"),        true)
            .set(field("hora_llegada_real"), OffsetDateTime.now())
            .where(field("id_viaje", Integer.class).eq(idViaje))
            .and(field("orden", Integer.class).eq(orden))
            .and(field("finalizado", Boolean.class).isFalse())
            .execute();

        if (filas > 0) return true;
        // Si no actualizó: o no existe, o ya estaba finalizada. Verificamos.
        return dsl.fetchExists(
            dsl.selectFrom(table("paradas_viaje"))
               .where(field("id_viaje", Integer.class).eq(idViaje))
               .and(field("orden", Integer.class).eq(orden))
        );
    }

    private ParadaDTO recordToDTO(Record r) {
        return ParadaDTO.builder()
                .idParada(r.get("id_parada", Integer.class))
                .orden(r.get("orden", Integer.class))
                .lat(r.get("lat", Double.class))
                .lng(r.get("lng", Double.class))
                .nombre(r.get("nombre", String.class))
                .distanciaAlSiguiente(r.get("distancia_al_siguiente", Integer.class))
                .tiempoAlSiguiente(r.get("tiempo_al_siguiente", Integer.class))
                .finalizado(r.get("finalizado", Boolean.class))
                .horaLlegadaReal(r.get("hora_llegada_real", OffsetDateTime.class))
                .build();
    }
}
