package ti.mdva.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Profile;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.web.SecurityFilterChain;

/**
 * Configuración de Spring Security.
 *
 * Perfil "dev":  todos los endpoints son públicos (sin autenticación).
 * Perfil "prod": solo /actuator/health es público; el resto requiere auth.
 *
 * Activar con: --spring.profiles.active=dev
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /**
     * Perfil DEV — permite todo sin autenticación.
     * Deshabilita CSRF para facilitar pruebas con curl/Postman/Swagger.
     */
    @Bean
    @Profile("dev")
    public SecurityFilterChain devSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .anyRequest().permitAll()
            );
        return http.build();
    }

    /**
     * Perfil PROD — solo expone el health check públicamente.
     * El resto de endpoints queda protegido (configura autenticación real aquí).
     */
    @Bean
    @Profile("prod")
    public SecurityFilterChain prodSecurityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/actuator/health").permitAll()
                .requestMatchers("/swagger-ui.html", "/swagger-ui/**", "/api-docs/**").permitAll()
                .anyRequest().authenticated()
            );
        return http.build();
    }
}
