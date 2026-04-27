package ti.mdva.exception;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.core.MethodParameter;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.validation.BeanPropertyBindingResult;
import org.springframework.validation.FieldError;

import java.lang.reflect.Method;

import static org.assertj.core.api.Assertions.assertThat;

class GlobalExceptionHandlerTest {

    private final GlobalExceptionHandler handler = new GlobalExceptionHandler();

    @Test
    @DisplayName("BadCredentialsException → 401 con título 'Credenciales inválidas'")
    void mapeaBadCredentialsA401() {
        ProblemDetail pd = handler.handleBadCredentials(new BadCredentialsException("usuario o pass incorrectos"));

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.UNAUTHORIZED.value());
        assertThat(pd.getTitle()).isEqualTo("Credenciales inválidas");
        assertThat(pd.getDetail()).contains("usuario o pass");
        assertThat(pd.getProperties()).containsKey("timestamp");
    }

    @Test
    @DisplayName("IllegalArgumentException → 400 con título 'Argumento inválido'")
    void mapeaIllegalArgumentA400() {
        ProblemDetail pd = handler.handleIllegalArgument(
                new IllegalArgumentException("placa invalida ABC"));

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST.value());
        assertThat(pd.getTitle()).isEqualTo("Argumento inválido");
        assertThat(pd.getDetail()).contains("placa invalida");
    }

    @Test
    @DisplayName("IllegalStateException → 409 con título 'Estado inválido'")
    void mapeaIllegalStateA409() {
        ProblemDetail pd = handler.handleIllegalState(
                new IllegalStateException("el viaje ya fue finalizado"));

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.CONFLICT.value());
        assertThat(pd.getTitle()).isEqualTo("Estado inválido");
        assertThat(pd.getDetail()).contains("finalizado");
    }

    @Test
    @DisplayName("HttpClientErrorException de API externa → 502")
    void mapeaHttpClientErrorA502() {
        HttpClientErrorException ex = HttpClientErrorException.create(
                HttpStatus.NOT_FOUND, "Not Found", null, null, null);

        ProblemDetail pd = handler.handleGoogleApiClientError(ex);

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.BAD_GATEWAY.value());
        assertThat(pd.getTitle()).isEqualTo("Error de API externa");
    }

    @Test
    @DisplayName("ResourceAccessException → 503")
    void mapeaResourceAccessA503() {
        ProblemDetail pd = handler.handleResourceAccess(
                new ResourceAccessException("connection refused"));

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.SERVICE_UNAVAILABLE.value());
        assertThat(pd.getTitle()).isEqualTo("Servicio no disponible");
    }

    @Test
    @DisplayName("RuntimeException genérica → 500")
    void mapeaRuntimeA500() {
        ProblemDetail pd = handler.handleRuntime(new RuntimeException("algo raro paso"));

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.INTERNAL_SERVER_ERROR.value());
        assertThat(pd.getTitle()).isEqualTo("Error interno");
    }

    @Test
    @DisplayName("MethodArgumentNotValidException → 400 concatenando errores de campo")
    void mapeaValidationA400ConErroresDeCampo() throws Exception {
        // Construimos un MethodArgumentNotValidException real con dos FieldErrors
        BeanPropertyBindingResult bindingResult = new BeanPropertyBindingResult(new Object(), "request");
        bindingResult.addError(new FieldError("request", "username", "no debe estar vacío"));
        bindingResult.addError(new FieldError("request", "email", "formato inválido"));

        Method method = DummyController.class.getDeclaredMethod("dummy", Object.class);
        MethodParameter param = new MethodParameter(method, 0);

        MethodArgumentNotValidException ex = new MethodArgumentNotValidException(param, bindingResult);

        ProblemDetail pd = handler.handleValidation(ex);

        assertThat(pd.getStatus()).isEqualTo(HttpStatus.BAD_REQUEST.value());
        assertThat(pd.getTitle()).isEqualTo("Error de validación");
        assertThat(pd.getDetail())
                .contains("username")
                .contains("email")
                .contains("no debe estar vacío")
                .contains("formato inválido");
    }

    // Helper para construir un MethodParameter válido
    static class DummyController {
        public void dummy(Object body) {}
    }
}
