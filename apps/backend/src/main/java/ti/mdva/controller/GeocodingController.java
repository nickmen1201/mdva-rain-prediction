package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import ti.mdva.service.geocoding.GeocodingResultDTO;
import ti.mdva.service.geocoding.NominatimClient;
import ti.mdva.service.geocoding.PhotonClient;

import java.util.List;

/** Búsqueda de direcciones con Nominatim (contrato: specs/008-backend-routing-nominatim/contracts). */
@RestController
@RequestMapping("/api/geocoding")
@Tag(name = "Geocoding", description = "Direcciones del Valle de Aburrá (Nominatim/OSM)")
public class GeocodingController {

    private final NominatimClient nominatim;
    private final PhotonClient photon;

    public GeocodingController(NominatimClient nominatim, PhotonClient photon) {
        this.nominatim = nominatim;
        this.photon = photon;
    }

    @GetMapping("/suggest")
    @Operation(
        summary = "Sugerencias mientras se escribe (máx. 5)",
        description = "Texto parcial (≥ 3 caracteres) con Photon/OSM, limitado al Valle de Aburrá. Caché de 30 min."
    )
    public List<GeocodingResultDTO> suggest(@RequestParam("q") String q) {
        return photon.suggest(q);
    }

    @GetMapping("/search")
    @Operation(
        summary = "Lugares que coinciden con un texto (máx. 5)",
        description = "Búsqueda al enviar el texto, no por tecla (política de Nominatim). Caché de 24 h."
    )
    public List<GeocodingResultDTO> search(@RequestParam("q") String q) {
        return nominatim.search(q);
    }

    @GetMapping("/reverse")
    @Operation(summary = "Dirección legible de un punto", description = "404 si no hay dirección para el punto.")
    public ResponseEntity<GeocodingResultDTO> reverse(@RequestParam("lat") double lat, @RequestParam("lng") double lng) {
        if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
            throw new IllegalArgumentException("Coordenadas fuera de rango.");
        }
        return nominatim.reverse(lat, lng).map(ResponseEntity::ok).orElse(ResponseEntity.notFound().build());
    }
}
