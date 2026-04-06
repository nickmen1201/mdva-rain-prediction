package ti.mdva.config;

import org.jooq.Configuration;
import org.springframework.context.annotation.Bean;

import ti.mdva.jooq.tables.daos.UsuariosDao;
import ti.mdva.jooq.tables.daos.VehiculosDao;
import ti.mdva.jooq.tables.daos.ViajesDao;

/**
 * Registra los DAOs generados por JOOQ como beans de Spring.
 *
 * Los DAOs de JOOQ no tienen @Component ni @Repository porque son código
 * generado. Esta config los instancia con el Configuration de JOOQ que
 * Spring Boot ya gestiona vía spring-boot-starter-jooq.
 *
 * IMPORTANTE: Esta clase debe estar en el paquete ti.mdva.config (o cualquier
 * subpaquete de ti.mdva) para que @SpringBootApplication la encuentre en el
 * component scan. No debe vivir en ti.mdva.jooq.* (paquete generado).
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
