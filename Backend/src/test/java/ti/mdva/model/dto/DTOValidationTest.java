package ti.mdva.model.dto;

import jakarta.validation.ConstraintViolation;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests de Bean Validation en los DTOs de entrada.
 * Garantiza que los requests inválidos sean rechazados antes de tocar lógica de negocio.
 */
class DTOValidationTest {

    private static Validator validator;

    @BeforeAll
    static void setup() {
        try (ValidatorFactory factory = Validation.buildDefaultValidatorFactory()) {
            validator = factory.getValidator();
        }
    }

    @Nested
    @DisplayName("LocationPointDTO")
    class LocationPoint {

        @Test
        void latitudFueraDeRangoFalla() {
            var dto = LocationPointDTO.builder().lat(91.0).lng(0.0).build();
            Set<ConstraintViolation<LocationPointDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("lat"));
        }

        @Test
        void longitudFueraDeRangoFalla() {
            var dto = LocationPointDTO.builder().lat(0.0).lng(181.0).build();
            Set<ConstraintViolation<LocationPointDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("lng"));
        }

        @Test
        void coordenadasValidasPasan() {
            var dto = LocationPointDTO.builder().lat(6.2442).lng(-75.5812).build();
            assertThat(validator.validate(dto)).isEmpty();
        }
    }

    @Nested
    @DisplayName("TripRequestDTO")
    class TripRequest {

        @Test
        void origenNullFalla() {
            var dto = TripRequestDTO.builder()
                    .destino(LocationPointDTO.builder().lat(6.0).lng(-75.0).build())
                    .build();
            Set<ConstraintViolation<TripRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("origen"));
        }

        @Test
        void destinoNullFalla() {
            var dto = TripRequestDTO.builder()
                    .origen(LocationPointDTO.builder().lat(6.0).lng(-75.0).build())
                    .build();
            Set<ConstraintViolation<TripRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("destino"));
        }

        @Test
        void requestValidaPasa() {
            var dto = TripRequestDTO.builder()
                    .origen(LocationPointDTO.builder().lat(6.0).lng(-75.0).build())
                    .destino(LocationPointDTO.builder().lat(6.5).lng(-75.5).build())
                    .build();
            assertThat(validator.validate(dto)).isEmpty();
        }

        @Test
        void paradaInvalidaEnListaPropagaError() {
            // Una parada con lat fuera de rango debe disparar @Valid en cascada
            var dto = TripRequestDTO.builder()
                    .origen(LocationPointDTO.builder().lat(6.0).lng(-75.0).build())
                    .destino(LocationPointDTO.builder().lat(6.5).lng(-75.5).build())
                    .paradas(java.util.List.of(
                            LocationPointDTO.builder().lat(200.0).lng(0.0).build()
                    ))
                    .build();
            Set<ConstraintViolation<TripRequestDTO>> v = validator.validate(dto);
            assertThat(v).isNotEmpty();
        }
    }

    @Nested
    @DisplayName("RegisterRequestDTO")
    class Register {

        @Test
        void passwordCortoFalla() {
            var dto = RegisterRequestDTO.builder()
                    .nombre("Juan")
                    .username("juan01")
                    .email("juan@example.com")
                    .password("123")  // < 8 chars
                    .build();
            Set<ConstraintViolation<RegisterRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("password"));
        }

        @Test
        void emailMalFormadoFalla() {
            var dto = RegisterRequestDTO.builder()
                    .nombre("Juan")
                    .username("juan01")
                    .email("no-es-email")
                    .password("12345678")
                    .build();
            Set<ConstraintViolation<RegisterRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("email"));
        }

        @Test
        void usernameVacioFalla() {
            var dto = RegisterRequestDTO.builder()
                    .nombre("Juan")
                    .username("")
                    .email("juan@example.com")
                    .password("12345678")
                    .build();
            Set<ConstraintViolation<RegisterRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("username"));
        }

        @Test
        void requestValidaPasa() {
            var dto = RegisterRequestDTO.builder()
                    .nombre("Juan Pérez")
                    .username("juanp")
                    .email("juan@example.com")
                    .password("supersegura123")
                    .build();
            assertThat(validator.validate(dto)).isEmpty();
        }
    }

    @Nested
    @DisplayName("LoginRequestDTO")
    class Login {

        @Test
        void usernameNullFalla() {
            var dto = LoginRequestDTO.builder().password("xxxxxxxx").build();
            Set<ConstraintViolation<LoginRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("username"));
        }

        @Test
        void passwordNullFalla() {
            var dto = LoginRequestDTO.builder().username("juan").build();
            Set<ConstraintViolation<LoginRequestDTO>> v = validator.validate(dto);
            assertThat(v).anyMatch(c -> c.getPropertyPath().toString().equals("password"));
        }
    }
}
