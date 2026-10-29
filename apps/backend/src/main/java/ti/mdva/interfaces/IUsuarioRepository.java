package ti.mdva.interfaces;

import ti.mdva.jooq.tables.pojos.Usuarios;

import java.util.Optional;

/**
 * Port (interface) for Usuario persistence operations.
 * Defined in the ports layer — no JOOQ or Spring details here.
 * Implemented by UsuarioRepository in the infrastructure layer.
 */
public interface IUsuarioRepository {

    /**
     * Persists a new usuario or updates an existing one.
     * @param usuario the usuario to save
     * @return the saved usuario, with id populated if newly created
     */
    Usuarios save(Usuarios usuario);

    /**
     * Finds a usuario by its primary key.
     */
    Optional<Usuarios> findById(Long id);

    /**
     * Finds a usuario by their unique username.
     */
    Optional<Usuarios> findByUsername(String username);

    /**
     * Finds a usuario by their unique email.
     */
    Optional<Usuarios> findByEmail(String email);

    /**
     * Returns true if a username is already taken.
     */
    boolean existsByUsername(String username);

    /**
     * Returns true if an email is already registered.
     */
    boolean existsByEmail(String email);
}