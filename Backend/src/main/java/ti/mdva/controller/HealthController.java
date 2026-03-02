package ti.mdva.controller;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.Instant;
import java.util.Map;

/**
 * Health check endpoint for monitoring service status.
 */
@RestController
@RequestMapping("/api/health")
@Tag(name = "Health", description = "Service health monitoring endpoints")
public class HealthController {

    @GetMapping
    @Operation(summary = "Check service health", description = "Returns service status and timestamp")
    public ResponseEntity<Map<String, Object>> health() {
        return ResponseEntity.ok(Map.of(
                "status", "UP",
                "service", "mdva-backend",
                "timestamp", Instant.now().toString()
        ));
    }
}
