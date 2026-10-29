package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.jooq.Record;
import org.springframework.stereotype.Repository;

import java.time.OffsetDateTime;
import java.util.Optional;

import static org.jooq.impl.DSL.field;
import static org.jooq.impl.DSL.table;

/**
 * Repositorio para condiciones_snapshot.
 * Usa DSLContext directamente (las tablas V4 aún no tienen código JOOQ generado).
 */
@Repository
public class CondicionesSnapshotRepository {

    private final DSLContext dsl;

    public CondicionesSnapshotRepository(DSLContext dsl) {
        this.dsl = dsl;
    }

    public void save(int idViaje,
                     double probRf,
                     double probRl,
                     double temperaturaC,
                     double humedadPct,
                     double coberturaPct,
                     double vientoMs,
                     String alertaNivelInicio,
                     OffsetDateTime timestampDatoWeather) {

        dsl.insertInto(table("condiciones_snapshot"))
           .set(field("id_viaje"),               idViaje)
           .set(field("probabilidad_rf"),         probRf)
           .set(field("probabilidad_rl"),         probRl)
           .set(field("temperatura_c"),           temperaturaC)
           .set(field("humedad_pct"),             humedadPct)
           .set(field("cobertura_nubosa_pct"),    coberturaPct)
           .set(field("velocidad_viento_ms"),     vientoMs)
           .set(field("alerta_nivel_inicio"),     alertaNivelInicio)
           .set(field("timestamp_snapshot"),      OffsetDateTime.now())
           .set(field("timestamp_dato_weather"),  timestampDatoWeather)
           .onConflict(field("id_viaje"))
           .doNothing()
           .execute();
    }

    public Optional<SnapshotData> findByViajeId(int idViaje) {
        Record r = dsl.select()
                      .from(table("condiciones_snapshot"))
                      .where(field("id_viaje").eq(idViaje))
                      .fetchOne();

        if (r == null) return Optional.empty();

        return Optional.of(new SnapshotData(
            r.get(field("probabilidad_rf"),        Double.class),
            r.get(field("temperatura_c"),          Double.class),
            r.get(field("timestamp_snapshot"),     OffsetDateTime.class),
            r.get(field("timestamp_dato_weather"), OffsetDateTime.class)
        ));
    }

    /** Datos relevantes del snapshot para comparación en el monitor. */
    public record SnapshotData(
        Double probRfInicio,
        Double temperaturaInicio,
        OffsetDateTime timestampSnapshot,
        OffsetDateTime timestampDatoWeather
    ) {}
}
