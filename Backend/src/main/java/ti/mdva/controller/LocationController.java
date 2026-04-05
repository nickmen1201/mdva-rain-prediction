package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import ti.mdva.model.dto.CommuneDTO;
import ti.mdva.model.dto.MunicipalityDTO;
import ti.mdva.model.dto.NeighborhoodDTO;
import ti.mdva.service.LocationService;

import java.util.List;

/**
 * Controller for location-related endpoints (municipalities, communes, neighborhoods).
 */
@RestController
@RequestMapping("/api/locations")
@Tag(name = "Locations", description = "Geographic location management endpoints")
public class LocationController {

    private final LocationService locationService;

    public LocationController(LocationService locationService) {
        this.locationService = locationService;
    }

    @GetMapping("/municipalities")
    @Operation(summary = "Get all municipalities", description = "Returns list of all municipalities")
    public ResponseEntity<List<MunicipalityDTO>> getAllMunicipalities() {
        return ResponseEntity.ok(locationService.getAllMunicipalities());
    }

    @GetMapping("/municipalities/{id}/communes")
    @Operation(summary = "Get communes by municipality", description = "Returns all communes for a given municipality")
    public ResponseEntity<List<CommuneDTO>> getCommunesByMunicipality(@PathVariable String id) {
        return ResponseEntity.ok(locationService.getCommunesByMunicipality(id));
    }

    @GetMapping("/communes/{id}/neighborhoods")
    @Operation(summary = "Get neighborhoods by commune", description = "Returns all neighborhoods for a given commune")
    public ResponseEntity<List<NeighborhoodDTO>> getNeighborhoodsByCommune(@PathVariable String id) {
        return ResponseEntity.ok(locationService.getNeighborhoodsByCommune(id));
    }
}
