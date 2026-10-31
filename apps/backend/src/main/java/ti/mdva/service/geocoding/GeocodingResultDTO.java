package ti.mdva.service.geocoding;

/**
 * Lugar encontrado por texto o por coordenadas.
 *
 * @param tipo tipo de lugar según OSM (p. ej. {@code museum}, {@code residential})
 */
public record GeocodingResultDTO(String displayName, double lat, double lng, String tipo) {}
