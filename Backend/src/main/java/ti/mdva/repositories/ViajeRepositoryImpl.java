package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.springframework.stereotype.Repository;
import ti.mdva.jooq.tables.daos.ViajesDao;
import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.interfaces.IViajeRepository;

import java.util.List;
import java.util.Optional;

import static ti.mdva.jooq.tables.Viajes.VIAJES;

// Implementación de la interfaz usando JOOQ para la persistencia de Viaje

@Repository
public class ViajeRepositoryImpl implements IViajeRepository {

    private final ViajesDao viajesDao;
    private final DSLContext dsl;

    public ViajeRepositoryImpl(ViajesDao viajesDao, DSLContext dsl) {
        this.viajesDao = viajesDao;
        this.dsl = dsl;
    }

    // La operacion save maneja la creación y sobreescritura de viajes
    @Override
    public Viajes save(Viajes viaje) {
        if (viaje.getIdViaje() == null) {
            // Insert: use DSLContext to get the generated ID back
            Integer generatedId = dsl.insertInto(VIAJES)
                    .set(VIAJES.ID_USUARIO,          viaje.getIdUsuario())
                    .set(VIAJES.ID_VEHICULO,         viaje.getIdVehiculo())
                    .set(VIAJES.ID_BARRIO_ORIGEN,    viaje.getIdBarrioOrigen())
                    .set(VIAJES.ID_BARRIO_DESTINO,   viaje.getIdBarrioDestino())
                    .set(VIAJES.TIEMPO_ESTIMADO_MIN, viaje.getTiempoEstimadoMin())
                    .set(VIAJES.HORA_INICIO,         viaje.getHoraInicio())
                    .set(VIAJES.PRECIPITACION_MM,    viaje.getPrecipitacionMm())
                    .set(VIAJES.FINALIZADO,          viaje.getFinalizado())
                    .returningResult(VIAJES.ID_VIAJE)
                    .fetchOneInto(Integer.class);

            viaje.setIdViaje(generatedId);
            return viaje;
        } 
        
        else {
            // Update: delegate to DAO which handles it by primary key
            viajesDao.update(viaje);
            return viaje;
        }
    }

    // Búsqueda de viajes por id
    @Override
    public Optional<Viajes> findById(Integer idViaje) {
        return viajesDao.fetchOptionalByIdViaje(idViaje);
    }

    // Búsqueda de viajes por idUsuario
    @Override
    public List<Viajes> findByUsuario(Integer idUsuario) {
        return viajesDao.fetchByIdUsuario(idUsuario);
    }
}