package ti.mdva.interfaces;

import ti.mdva.jooq.tables.pojos.Viajes;

import java.util.List;
import java.util.Optional;

/**
 * Port (interface) for Viaje persistence operations.
 * Defined in the application layer — no JOOQ or Spring Data details here.
 * Implemented by ViajeRepositoryImpl in the infrastructure layer.
 */
public interface IViajeRepository {

    /**
     * Persists a new viaje or updates an existing one.
     * @param viaje the viaje to save
     * @return the saved viaje, with idViaje populated if newly created
     */
    Viajes save(Viajes viaje);

    /**
     * Finds a viaje by its primary key.
     * @param idViaje the trip ID
     * @return an Optional containing the viaje if found
     */
    Optional<Viajes> findById(Integer idViaje);

    /**
     * Returns all viajes for a given user.
     * @param idUsuario the user ID
     * @return list of viajes, empty if none found
     */
    List<Viajes> findByUsuario(Integer idUsuario);
}