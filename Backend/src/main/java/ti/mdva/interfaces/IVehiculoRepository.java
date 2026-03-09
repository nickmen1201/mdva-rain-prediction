package ti.mdva.interfaces;

import ti.mdva.jooq.tables.pojos.Vehiculos;

import java.util.List;
import java.util.Optional;

/**
 * Port (interface) for Vehiculo persistence operations.
 * Defined in the ports layer — no JOOQ or Spring details here.
 * Implemented by VehiculoRepository in the infrastructure layer.
 */
public interface IVehiculoRepository {

    /**
     * Persists a new vehiculo or updates an existing one.
     * Note: placa is the PK and must always be provided by the caller —
     * there is no DB-generated ID for this entity.
     *
     * @param vehiculo the vehiculo to save
     * @return the saved vehiculo
     */
    Vehiculos save(Vehiculos vehiculo);

    /**
     * Finds a vehiculo by its primary key (placa).
     */
    Optional<Vehiculos> findByPlaca(String placa);

    /**
     * Returns all vehiculos owned by a given user.
     */
    List<Vehiculos> findByUsuario(Integer idUsuario);

    /**
     * Returns true if a vehiculo with the given placa already exists.
     */
    boolean existsByPlaca(String placa);
}