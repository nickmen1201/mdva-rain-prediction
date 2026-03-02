package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * Health check controller.
 *
 * @author MDVA Team
 * @version 1.0
 */
@RestController
@RequestMapping("/api/v1/health")
@Tag(name = "Health", description = "Service health check endpoints")
public class HealthController {

    @GetMapping
    @Operation(summary = "Check service health")
    public ResponseEntity<Map<String, Object>> checkHealth() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "timestamp", LocalDateTime.now(),
                "service", "MDVA Backend"
        ));
    }
}
