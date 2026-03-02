package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ti.mdva.dto.CommuneDTO;
import ti.mdva.dto.MunicipalityDTO;
import ti.mdva.dto.NeighborhoodDTO;
import ti.mdva.service.LocationService;

import java.util.List;

/**
 * Location management controller.
 *
 * @author MDVA Team
 * @version 1.0
 */
@RestController
@RequestMapping("/api/v1/locations")
@RequiredArgsConstructor
@Tag(name = "Locations", description = "Geographic location endpoints")
public class LocationController {

    private final LocationService locationService;

    @GetMapping("/municipalities")
    @Operation(summary = "List all municipalities")
    public ResponseEntity<List<MunicipalityDTO>> getAllMunicipalities() {
        return ResponseEntity.ok(locationService.getAllMunicipalities());
    }

    @GetMapping("/municipalities/{municipalityId}/communes")
    @Operation(summary = "List communes by municipality")
    public ResponseEntity<List<CommuneDTO>> getCommunesByMunicipality(@PathVariable String municipalityId) {
        return ResponseEntity.ok(locationService.getCommunesByMunicipality(municipalityId));
    }

    @GetMapping("/communes/{communeId}/neighborhoods")
    @Operation(summary = "List neighborhoods by commune")
    public ResponseEntity<List<NeighborhoodDTO>> getNeighborhoodsByCommune(@PathVariable String communeId) {
        return ResponseEntity.ok(locationService.getNeighborhoodsByCommune(communeId));
    }
}
