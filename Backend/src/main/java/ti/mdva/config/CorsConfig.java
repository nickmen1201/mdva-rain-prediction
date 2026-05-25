package ti.mdva.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;

import java.util.Arrays;
import java.util.List;

/**
 * CORS configuration for cross-origin requests.
 *
 * En desarrollo permite cualquier origen reflejado. En producción debe configurarse
 * la variable de entorno {@code CORS_ALLOWED_ORIGINS} con la URL exacta del frontend
 * (ej. {@code https://mdva.tu-dominio.co}). Acepta varios separados por coma.
 */
@Configuration
public class CorsConfig {

    private final String allowedOrigins;

    public CorsConfig(@Value("${cors.allowed-origins:*}") String allowedOrigins) {
        this.allowedOrigins = allowedOrigins;
    }

    @Bean
    public CorsFilter corsFilter() {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowCredentials(true);

        List<String> origins = Arrays.stream(allowedOrigins.split(","))
                .map(String::trim)
                .filter(s -> !s.isEmpty())
                .toList();
        config.setAllowedOriginPatterns(origins.isEmpty() ? List.of("*") : origins);

        config.setAllowedHeaders(List.of("*"));
        config.setAllowedMethods(Arrays.asList("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"));

        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);

        return new CorsFilter(source);
    }
}
