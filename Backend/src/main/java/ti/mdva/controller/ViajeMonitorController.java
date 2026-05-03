package ti.mdva.controller;

import jakarta.validation.Valid;
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
public class ViajeMonitorController {

    private final TripMonitorServiceImpl tripMonitorService;
    private final AlertaViajeRepository  alertaViajeRepository;

    public ViajeMonitorController(TripMonitorServiceImpl tripMonitorService,
                                   AlertaViajeRepository alertaViajeRepository) {
        this.tripMonitorService   = tripMonitorService;
        this.alertaViajeRepository = alertaViajeRepository;
    }

    @PostMapping("/posicion")
    public ResponseEntity<MonitoreoResponseDTO> reportarPosicion(
            @PathVariable Integer id,
            @RequestBody @Valid PosicionRequest req
    ) {
        MonitoreoResponseDTO res = tripMonitorService.evaluarPosicion(id, req.latActual(), req.lngActual());
        return ResponseEntity.ok(res);
    }

    @GetMapping("/alertas")
    public ResponseEntity<List<AlertaViajeDTO>> obtenerAlertas(@PathVariable Integer id) {
        return ResponseEntity.ok(alertaViajeRepository.findByViajeId(id));
    }

    @PatchMapping("/alertas/{idAlerta}/leer")
    public ResponseEntity<Void> marcarLeida(
            @PathVariable Integer id,
            @PathVariable Integer idAlerta
    ) {
        alertaViajeRepository.marcarComoLeida(idAlerta);
        return ResponseEntity.ok().build();
    }

    /** DTO de request para reportar posición. */
    public record PosicionRequest(Double latActual, Double lngActual) {}
}
