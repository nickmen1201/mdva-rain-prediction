package ti.mdva.service.routing;

import ti.mdva.model.dto.RouteStepDTO;

import java.util.List;

/**
 * Ruta calculada por el routing service propio.
 *
 * @param durationSeconds duración base, sin ajuste por lluvia (RF-10 lo aplica el Backend)
 * @param alternative     ruta alternativa con geometría distinta, o {@code null}
 */
public record RouteResult(
        int durationSeconds,
        int distanceMeters,
        String overviewPolyline,
        List<RouteStepDTO> steps,
        Alternative alternative
) {

    /** Ruta alternativa ofrecida por el routing service (RF-14). */
    public record Alternative(String routeType, int durationSeconds, int distanceMeters, String overviewPolyline) {}
}
