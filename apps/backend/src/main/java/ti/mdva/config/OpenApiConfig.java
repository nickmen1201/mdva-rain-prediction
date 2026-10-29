package ti.mdva.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * OpenAPI/Swagger documentation configuration.
 *
 * Define el esquema de seguridad bearerAuth (JWT) para que aparezca el botón
 * "Authorize" (candado) en Swagger UI y se inyecte el header
 *   Authorization: Bearer <token>
 * en cada request a endpoints protegidos.
 */
@Configuration
public class OpenApiConfig {

    private static final String BEARER_KEY = "bearerAuth";

    @Bean
    public OpenAPI mdvaOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("MDVA API")
                        .description("Environmental Variables Monitoring API for Urban Mobility in Medellin")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("MDVA Team")
                                .email("mdva@example.com"))
                        .license(new License()
                                .name("MIT License")
                                .url("https://opensource.org/licenses/MIT")))
                .servers(List.of(
                        new Server().url("http://localhost:8080").description("Local Development")
                ))
                .addSecurityItem(new SecurityRequirement().addList(BEARER_KEY))
                .components(new Components()
                        .addSecuritySchemes(BEARER_KEY, new SecurityScheme()
                                .type(SecurityScheme.Type.HTTP)
                                .scheme("bearer")
                                .bearerFormat("JWT")
                                .description("Pegá el JWT que recibís en /auth/login (sin el prefijo 'Bearer ')")
                        )
                );
    }
}
