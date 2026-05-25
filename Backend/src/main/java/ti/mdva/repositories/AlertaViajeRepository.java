package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.jooq.Record;
import org.jooq.Result;
import org.springframework.stereotype.Repository;
import ti.mdva.model.dto.AlertaViajeDTO;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.stream.Collectors;

import static org.jooq.impl.DSL.field;
import static org.jooq.impl.DSL.table;

/**
 * Repositorio para alertas_viaje.
 * Usa DSLContext directamente (tablas V4 pendientes de regeneración JOOQ).
 */
@Repository
public class AlertaViajeRepository {

    private final DSLContext dsl;

    public AlertaViajeRepository(DSLContext dsl) {
        this.dsl = dsl;
    }

    /**
     * Persiste una nueva alerta y retorna su ID generado.
     */
    public Integer save(AlertaViajeDTO alerta, int idViaje, double lat, double lng,
                        double probRfActual, boolean conLatencia) {
        return dsl.insertInto(table("alertas_viaje"))
            .set(field("id_viaje"),               idViaje)
            .set(field("tipo_alerta"),             alerta.getTipoAlerta())
            .set(field("nivel_severidad"),         alerta.getNivelSeveridad())
            .set(field("accion_sugerida"),         alerta.getAccionSugerida())
            .set(field("mensaje"),                 alerta.getMensaje())
            .set(field("detalle_recomendacion"),   alerta.getDetalleRecomendacion())
            .set(field("lat_posicion"),            lat)
            .set(field("lng_posicion"),            lng)
            .set(field("probabilidad_rf_actual"),  probRfActual)
            .set(field("dato_con_latencia"),       conLatencia)
            .set(field("timestamp_generacion"),    OffsetDateTime.now())
            .set(field("leida"),                   false)
            .returningResult(field("id_alerta"))
            .fetchOneInto(Integer.class);
    }

    /**
     * Lista todas las alertas de un viaje, ordenadas de más reciente a más antigua.
     */
    public List<AlertaViajeDTO> findByViajeId(int idViaje) {
        Result<Record> rows = dsl.select()
            .from(table("alertas_viaje"))
            .where(field("id_viaje").eq(idViaje))
            .orderBy(field("timestamp_generacion").desc())
            .fetch();

        return rows.stream().map(r -> AlertaViajeDTO.builder()
            .idAlerta(r.get(field("id_alerta"), Integer.class))
            .tipoAlerta(r.get(field("tipo_alerta"), String.class))
            .nivelSeveridad(r.get(field("nivel_severidad"), String.class))
            .accionSugerida(r.get(field("accion_sugerida"), String.class))
            .mensaje(r.get(field("mensaje"), String.class))
            .detalleRecomendacion(r.get(field("detalle_recomendacion"), String.class))
            .datoConLatencia(r.get(field("dato_con_latencia"), Boolean.class))
            .timestampGeneracion(r.get(field("timestamp_generacion"), OffsetDateTime.class))
            .leida(r.get(field("leida"), Boolean.class))
            .build()
        ).collect(Collectors.toList());
    }

    /**
     * Marca una alerta como leída.
     */
    public void marcarComoLeida(int idAlerta) {
        dsl.update(table("alertas_viaje"))
           .set(field("leida"), true)
           .where(field("id_alerta").eq(idAlerta))
           .execute();
    }
}
