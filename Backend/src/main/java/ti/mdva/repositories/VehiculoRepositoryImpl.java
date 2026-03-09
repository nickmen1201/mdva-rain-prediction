package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.springframework.stereotype.Repository;
import ti.mdva.jooq.tables.daos.VehiculosDao;
import ti.mdva.jooq.tables.pojos.Vehiculos;
import ti.mdva.interfaces.IVehiculoRepository;

import java.util.List;
import java.util.Optional;

import static ti.mdva.jooq.tables.Vehiculos.VEHICULOS;

// Implementación de la interfaz usando JOOQ para la persistencia de Vehículos
@Repository
public class VehiculoRepositoryImpl implements IVehiculoRepository {

    private final VehiculosDao vehiculosDao;
    private final DSLContext dsl;

    public VehiculoRepositoryImpl(VehiculosDao vehiculosDao, DSLContext dsl) {
        this.vehiculosDao = vehiculosDao;
        this.dsl = dsl;
    }

   // Método para crear o sobreescribir un vehículo
    @Override
    public Vehiculos save(Vehiculos vehiculo) {
        if (vehiculosDao.fetchOptionalByPlaca(vehiculo.getPlaca()).isEmpty()) {
            vehiculosDao.insert(vehiculo);
        } 
        
        else {
            vehiculosDao.update(vehiculo);
        }
        return vehiculo;
    }


    // Métodos de búsqueda
    @Override
    public Optional<Vehiculos> findByPlaca(String placa) {
        return vehiculosDao.fetchOptionalByPlaca(placa);
    }

    @Override
    public List<Vehiculos> findByUsuario(Integer idUsuario) {
        return vehiculosDao.fetchByIdUsuario(idUsuario);
    }

    // Validación de existencia por placa
    @Override
    public boolean existsByPlaca(String placa) {
        return dsl.fetchExists(
            dsl.selectOne()
               .from(VEHICULOS)
               .where(VEHICULOS.PLACA.eq(placa))
        );
    }
}