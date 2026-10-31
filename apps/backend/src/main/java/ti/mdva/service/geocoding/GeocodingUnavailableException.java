package ti.mdva.service.geocoding;

/** El proveedor de geocodificación no respondió → 503. */
public class GeocodingUnavailableException extends RuntimeException {

    public GeocodingUnavailableException(String message, Throwable cause) {
        super(message, cause);
    }
}
