package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.DecimalMax;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.NotNull;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.service.impl.TripMonitorServiceImpl;

import java.util.List;

/**
 * Endpoints para el monitoreo activo de un trayecto en curso.
 *
 * POST  /api/viajes/{id}/posicion           → evalúa posición, retorna alerta si hay
 * GET   /api/viajes/{id}/alertas            → lista alertas del viaje
 * PATCH /api/viajes/{id}/alertas/{a}/leer   → marca alerta como leída
 */
@RestController
@RequestMapping("/api/viajes/{id}")
@Tag(name = "Monitoreo de viaje", description = "Reporte de posición y alertas activas durante el trayecto (Sprint 5.2A)")
public class ViajeMonitorController {

    private final TripMonitorServiceImpl tripMonitorService;
    private final AlertaViajeRepository  alertaViajeRepository;

    public ViajeMonitorController(TripMonitorServiceImpl tripMonitorService,
                                   AlertaViajeRepository alertaViajeRepository) {
        this.tripMonitorService   = tripMonitorService;
        this.alertaViajeRepository = alertaViajeRepository;
    }

    @PostMapping("/posicion")
    @Operation(
        summary = "Reportar posición actual durante un viaje",
        description = "Evalúa el cambio de condiciones desde el snapshot inicial. Devuelve alerta si el cambio amerita."
    )
    public ResponseEntity<MonitoreoResponseDTO> reportarPosicion(
            @PathVariable Integer id,
            @RequestBody @Valid PosicionRequest req
    ) {
        MonitoreoResponseDTO res = tripMonitorService.evaluarPosicion(id, req.latActual(), req.lngActual());
        return ResponseEntity.ok(res);
    }

    @GetMapping("/alertas")
    @Operation(
        summary = "Listar alertas del viaje",
        description = "Retorna alertas ordenadas de más reciente a más antigua. Filtro opcional soloNoLeidas."
    )
    public ResponseEntity<List<AlertaViajeDTO>> obtenerAlertas(
            @PathVariable Integer id,
            @RequestParam(defaultValue = "false") boolean soloNoLeidas
    ) {
        var todas = alertaViajeRepository.findByViajeId(id);
        if (soloNoLeidas) {
            todas = todas.stream()
                .filter(a -> !Boolean.TRUE.equals(a.getLeida()))
                .toList();
        }
        return ResponseEntity.ok(todas);
    }

    @PatchMapping("/alertas/{idAlerta}/leer")
    @Operation(summary = "Marcar una alerta como leída")
    public ResponseEntity<Void> marcarLeida(
            @PathVariable Integer id,
            @PathVariable Integer idAlerta
    ) {
        alertaViajeRepository.marcarComoLeida(idAlerta);
        return ResponseEntity.ok().build();
    }

    /** DTO de request para reportar posición. Validado con Bean Validation. */
    public record PosicionRequest(
            @NotNull(message = "latActual es obligatorio")
            @DecimalMin(value = "-90.0",  message = "Latitud fuera de rango")
            @DecimalMax(value = "90.0",   message = "Latitud fuera de rango")
            Double latActual,

            @NotNull(message = "lngActual es obligatorio")
            @DecimalMin(value = "-180.0", message = "Longitud fuera de rango")
            @DecimalMax(value = "180.0",  message = "Longitud fuera de rango")
            Double lngActual
    ) {}
}
