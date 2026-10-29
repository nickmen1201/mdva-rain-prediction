package ti.mdva.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;

import java.net.URI;
import java.time.Instant;
import java.util.stream.Collectors;

/**
 * Manejador global de excepciones.
 * Usa ProblemDetail (RFC 9457) para respuestas de error estructuradas.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    // ── Validación de DTOs ────────────────────────────────────────────────────

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail handleValidation(MethodArgumentNotValidException ex) {
        String detail = ex.getBindingResult().getFieldErrors().stream()
                .map(e -> e.getField() + ": " + e.getDefaultMessage())
                .collect(Collectors.joining(", "));

        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, detail);
        pd.setTitle("Error de validación");
        pd.setType(URI.create("https://mdva.ti/errors/validation"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    // ── Autenticación ─────────────────────────────────────────────────────────

    @ExceptionHandler(BadCredentialsException.class)
    public ProblemDetail handleBadCredentials(BadCredentialsException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.UNAUTHORIZED, ex.getMessage());
        pd.setTitle("Credenciales inválidas");
        pd.setType(URI.create("https://mdva.ti/errors/unauthorized"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    // ── Lógica de negocio ─────────────────────────────────────────────────────

    @ExceptionHandler(IllegalArgumentException.class)
    public ProblemDetail handleIllegalArgument(IllegalArgumentException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, ex.getMessage());
        pd.setTitle("Argumento inválido");
        pd.setType(URI.create("https://mdva.ti/errors/bad-argument"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    @ExceptionHandler(IllegalStateException.class)
    public ProblemDetail handleIllegalState(IllegalStateException ex) {
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(HttpStatus.CONFLICT, ex.getMessage());
        pd.setTitle("Estado inválido");
        pd.setType(URI.create("https://mdva.ti/errors/conflict"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    // ── Errores de API externa ────────────────────────────────────────────────

    @ExceptionHandler(HttpClientErrorException.class)
    public ProblemDetail handleGoogleApiClientError(HttpClientErrorException ex) {
        log.error("Error HTTP llamando a API externa: {} {}", ex.getStatusCode(), ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.BAD_GATEWAY,
                "Error en API externa: " + ex.getMessage()
        );
        pd.setTitle("Error de API externa");
        pd.setType(URI.create("https://mdva.ti/errors/external-api"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ProblemDetail handleResourceAccess(ResourceAccessException ex) {
        log.error("No se pudo conectar con servicio externo: {}", ex.getMessage());
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE,
                "No se pudo conectar con un servicio externo (Google Maps o ML). Reintenta en unos segundos."
        );
        pd.setTitle("Servicio no disponible");
        pd.setType(URI.create("https://mdva.ti/errors/service-unavailable"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }

    // ── Catch-all ─────────────────────────────────────────────────────────────

    @ExceptionHandler(RuntimeException.class)
    public ProblemDetail handleRuntime(RuntimeException ex) {
        log.error("Error inesperado: {}", ex.getMessage(), ex);
        ProblemDetail pd = ProblemDetail.forStatusAndDetail(
                HttpStatus.INTERNAL_SERVER_ERROR,
                ex.getMessage()
        );
        pd.setTitle("Error interno");
        pd.setType(URI.create("https://mdva.ti/errors/internal"));
        pd.setProperty("timestamp", Instant.now());
        return pd;
    }
}