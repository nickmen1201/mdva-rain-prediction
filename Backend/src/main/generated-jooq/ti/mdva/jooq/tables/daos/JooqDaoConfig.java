// CLASE GENERADA POR IA DEBIDO A ERRORES DE COMPILACIÓN A LA HORA DE LLAMAR A LOS DAOS

package ti.mdva.jooq.tables.daos;

import org.jooq.Configuration;
import org.springframework.context.annotation.Bean;
import ti.mdva.jooq.tables.daos.UsuariosDao;
import ti.mdva.jooq.tables.daos.VehiculosDao;
import ti.mdva.jooq.tables.daos.ViajesDao;

/**
 * Registers JOOQ-generated DAOs as Spring beans.
 *
 * JOOQ DAOs are not component-scanned automatically — they have no @Component
 * or @Repository annotation since they are generated code. This config bridges
 * that gap by constructing each DAO with the JOOQ Configuration that Spring
 * already manages (auto-configured by spring-boot-starter-jooq).
 */
@org.springframework.context.annotation.Configuration
public class JooqDaoConfig {

    @Bean
    public UsuariosDao usuariosDao(Configuration jooqConfiguration) {
        return new UsuariosDao(jooqConfiguration);
    }

    @Bean
    public VehiculosDao vehiculosDao(Configuration jooqConfiguration) {
        return new VehiculosDao(jooqConfiguration);
    }

    @Bean
    public ViajesDao viajesDao(Configuration jooqConfiguration) {
        return new ViajesDao(jooqConfiguration);
    }
}