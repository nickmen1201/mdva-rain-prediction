package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.TripRequestDTO;
import ti.mdva.model.dto.TripResponseDTO;
import ti.mdva.usecases.ViajeUseCase;

import java.net.URI;
import java.util.List;

/**
 * Controller REST para operaciones de viaje.
 *
 * POST  /api/viajes/planificar      → planifica ruta + ML, retorna TripResponseDTO
 * PATCH /api/viajes/{id}/finalizar  → marca el viaje como finalizado
 * GET   /api/viajes/usuario/{id}    → historial de viajes de un usuario
 * GET   /api/viajes/{id}            → obtener viaje por ID
 */
@RestController
@RequestMapping("/api/viajes")
@Tag(name = "Viajes", description = "Planificación y gestión de viajes con IA")
public class ViajeController {

    private final ViajeUseCase viajeUseCase;

    public ViajeController(ViajeUseCase viajeUseCase) {
        this.viajeUseCase = viajeUseCase;
    }

    @PostMapping("/planificar")
    @Operation(
        summary = "Planificar un viaje",
        description = "Calcula la ruta óptima con Google Directions, predice lluvia con el modelo ML " +
                      "y ajusta el tiempo estimado. Persiste el viaje en base de datos."
    )
    public ResponseEntity<TripResponseDTO> planificar(@Valid @RequestBody TripRequestDTO request) {
        TripResponseDTO response = viajeUseCase.planificarViaje(request);
        return ResponseEntity
                .created(URI.create("/api/viajes/" + response.getIdViaje()))
                .body(response);
    }

    @PatchMapping("/{id}/finalizar")
    @Operation(summary = "Finalizar un viaje", description = "Marca el viaje como finalizado y registra la hora de fin.")
    public ResponseEntity<Viajes> finalizar(@PathVariable Integer id) {
        return ResponseEntity.ok(viajeUseCase.finalizarViaje(id));
    }

    @GetMapping("/usuario/{idUsuario}")
    @Operation(summary = "Historial de viajes", description = "Retorna todos los viajes de un usuario.")
    public ResponseEntity<List<Viajes>> historial(@PathVariable Integer idUsuario) {
        return ResponseEntity.ok(viajeUseCase.findByUsuario(idUsuario));
    }

    @GetMapping("/{id}")
    @Operation(summary = "Obtener viaje por ID")
    public ResponseEntity<Viajes> getById(@PathVariable Integer id) {
        return viajeUseCase.findById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}