package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import ti.mdva.jooq.tables.pojos.Viajes;
import ti.mdva.model.dto.AlertaActualDTO;
import ti.mdva.model.dto.TripRequestDTO;
import ti.mdva.model.dto.TripResponseDTO;
import ti.mdva.usecases.ViajeUseCase;

import java.net.URI;
import java.util.List;
import java.security.Principal;
import ti.mdva.repositories.UsuarioRepositoryImpl;
import ti.mdva.jooq.tables.pojos.Usuarios;

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
    private final UsuarioRepositoryImpl usuarioRepository;

    public ViajeController(ViajeUseCase viajeUseCase, UsuarioRepositoryImpl usuarioRepository) {
        this.viajeUseCase = viajeUseCase;
        this.usuarioRepository = usuarioRepository;
    }

    @PostMapping("/planificar")
    @Operation(
        summary = "Planificar un viaje",
        description = "Calcula la ruta óptima con Google Directions, predice lluvia con el modelo ML " +
                      "y ajusta el tiempo estimado. Persiste el viaje en base de datos."
    )
    public ResponseEntity<TripResponseDTO> planificar(@Valid @RequestBody TripRequestDTO request, Principal principal) {
        if (principal == null) {
            return ResponseEntity.status(401).build();
        }
        Usuarios usuario = usuarioRepository.findByUsername(principal.getName())
                .orElseThrow(() -> new IllegalArgumentException("Usuario no encontrado"));
                
        TripResponseDTO response = viajeUseCase.planificarViaje(usuario.getId().intValue(), request);
        return ResponseEntity
                .created(URI.create("/api/viajes/" + response.getIdViaje()))
                .body(response);
    }

    @PatchMapping("/{id}/finalizar")
    @Operation(summary = "Finalizar un viaje", description = "Marca el viaje como finalizado, registra la hora de fin y opcionalmente la calificación.")
    public ResponseEntity<Viajes> finalizar(@PathVariable Integer id, @RequestParam(required = false) Short userRating) {
        return ResponseEntity.ok(viajeUseCase.finalizarViaje(id, userRating));
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

    @GetMapping("/{id}/alerta-actual")
    @Operation(
        summary = "Alerta climática actual del viaje (HU031)",
        description = "Recalcula la predicción de lluvia con el clima del momento sobre el " +
                      "origen del viaje y devuelve el nivel de alerta actualizado. La ruta no " +
                      "se recalcula. Solo el dueño del viaje puede consultarlo."
    )
    public ResponseEntity<AlertaActualDTO> alertaActual(@PathVariable Integer id, Principal principal) {
        if (principal == null) {
            return ResponseEntity.status(401).build();
        }
        Usuarios usuario = usuarioRepository.findByUsername(principal.getName())
                .orElseThrow(() -> new IllegalArgumentException("Usuario no encontrado"));

        return ResponseEntity.ok(
                viajeUseCase.obtenerAlertaActual(id, usuario.getId().intValue())
        );
    }
}