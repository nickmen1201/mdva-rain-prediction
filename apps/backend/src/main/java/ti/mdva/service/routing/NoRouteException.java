package ti.mdva.service.routing;

/** No existe una ruta en el grafo vial entre los puntos pedidos → 422. */
public class NoRouteException extends RuntimeException {

    public NoRouteException(String message, Throwable cause) {
        super(message, cause);
    }
}
