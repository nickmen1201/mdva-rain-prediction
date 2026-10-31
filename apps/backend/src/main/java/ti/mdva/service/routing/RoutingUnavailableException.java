package ti.mdva.service.routing;

/** El routing service no respondió (caído, timeout o error interno) → 503. */
public class RoutingUnavailableException extends RuntimeException {

    public RoutingUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
