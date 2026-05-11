package ti.mdva.service;

/**
 * Traduce los códigos de status de Google Maps Platform (Geocoding/Directions)
 * a mensajes en español accionables para el usuario final (KR1: comprensión).
 *
 * Si el status es desconocido, devuelve un mensaje genérico que indica el motivo
 * crudo para diagnóstico.
 */
public final class GoogleApiErrorTranslator {

    private GoogleApiErrorTranslator() {}

    /**
     * @param status      código retornado por Google Maps API (ZERO_RESULTS, NOT_FOUND, etc.)
     * @param esGeocoding true si el contexto es geocodificación, false si es cálculo de ruta
     */
    public static String traducir(String status, boolean esGeocoding) {
        return switch (status) {
            case "ZERO_RESULTS" -> esGeocoding
                ? "No encontramos ese lugar. Intenta con una dirección más específica."
                : "No encontramos una ruta entre esos puntos. Verifica que el origen y destino sean diferentes y estén en zonas con vías.";
            case "NOT_FOUND" -> "Una de las direcciones no fue reconocida. Intenta seleccionarla de las sugerencias.";
            case "MAX_WAYPOINTS_EXCEEDED" -> "Demasiadas paradas en el viaje. El máximo permitido es 5.";
            case "MAX_ROUTE_LENGTH_EXCEEDED" -> "La ruta es demasiado larga. Intenta con un destino más cercano.";
            case "INVALID_REQUEST" -> "La solicitud tiene datos inválidos. Verifica el origen y destino.";
            case "OVER_DAILY_LIMIT", "OVER_QUERY_LIMIT" -> "El servicio de mapas está saturado. Intenta de nuevo en unos segundos.";
            case "REQUEST_DENIED" -> "El servicio de mapas rechazó la solicitud. Reporta este error al equipo.";
            case "UNKNOWN_ERROR" -> "Error temporal del servicio de mapas. Intenta de nuevo.";
            case "NULL_RESPONSE" -> "No se obtuvo respuesta del servicio de mapas. Verifica tu conexión.";
            default -> (esGeocoding ? "No se pudo geocodificar el lugar: " : "No se pudo calcular la ruta: ") + status;
        };
    }
}
