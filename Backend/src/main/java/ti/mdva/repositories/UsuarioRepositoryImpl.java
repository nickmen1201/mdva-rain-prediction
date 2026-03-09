package ti.mdva.repositories;

import org.jooq.DSLContext;
import org.springframework.stereotype.Repository;
import ti.mdva.jooq.tables.daos.UsuariosDao;
import ti.mdva.jooq.tables.pojos.Usuarios;
import ti.mdva.interfaces.IUsuarioRepository;

import java.util.Optional;

import static ti.mdva.jooq.tables.Usuarios.USUARIOS;

/**
 * Implementación de la interfaz usando JOOQ para la persistencia de Usuarios.
 * (Esta clase es la única que conoce los detalles de JOOQ y hace su manejo directo para Usuarios).
 *
 * - Manejo de CRUD Usando UsuariosDao para operaciones simples basadas en PK.
 * - DSLContext nos permite usar SQL externo a JOOQ en caso de ser necesario.
 * 
 *  (El resto de los repositorios siguen esta misma estructura)
 */
@Repository
public class UsuarioRepositoryImpl implements IUsuarioRepository{

    private final UsuariosDao usuariosDao;
    private final DSLContext dsl;

    public UsuarioRepositoryImpl(UsuariosDao usuariosDao, DSLContext dsl) {
        this.usuariosDao = usuariosDao;
        this.dsl = dsl;
    }

    // La operacion save maneja la creación y sobreescritura de usuarios
    @Override
    public Usuarios save(Usuarios usuario) {
        if (usuario.getId() == null) {
            Long generatedId = dsl.insertInto(USUARIOS)
                    .set(USUARIOS.NOMBRE,            usuario.getNombre())
                    .set(USUARIOS.USERNAME,          usuario.getUsername())
                    .set(USUARIOS.EMAIL,             usuario.getEmail())
                    .set(USUARIOS.AUTHHASH,          usuario.getAuthhash())
                    .set(USUARIOS.FECHA_NACIMIENTO,  usuario.getFechaNacimiento())
                    .set(USUARIOS.CREADO_EN,         usuario.getCreadoEn())
                    .set(USUARIOS.ID_BARRIO,         usuario.getIdBarrio())
                    .returningResult(USUARIOS.ID)
                    .fetchOneInto(Long.class);

            usuario.setId(generatedId);
            return usuario;
        } else {
            usuariosDao.update(usuario);
            return usuario;
        }
    }

    // Métodos de búsqueda
    @Override
    public Optional<Usuarios> findById(Long id) {
        return usuariosDao.fetchOptionalById(id);
    }

    @Override
    public Optional<Usuarios> findByUsername(String username) {
        return usuariosDao.fetchOptionalByUsername(username);
    }

    @Override
    public Optional<Usuarios> findByEmail(String email) {
        return usuariosDao.fetchOptionalByEmail(email);
    }

    // -------------------------------------------------------------------------
    // existsByUsername / existsByEmail
    // -------------------------------------------------------------------------

   // Métodos de DSLContext para verificar existencias a la hora de crear usuarios
    @Override
    public boolean existsByUsername(String username) {
        return dsl.fetchExists(
            dsl.selectOne()
               .from(USUARIOS)
               .where(USUARIOS.USERNAME.eq(username))
        );
    }

    @Override
    public boolean existsByEmail(String email) {
        return dsl.fetchExists(
            dsl.selectOne()
               .from(USUARIOS)
               .where(USUARIOS.EMAIL.eq(email))
        );
    }
}