package ti.mdva.model.dto;

import java.time.Instant;
import java.util.List;

public record WeatherGridResponseDTO(
    List<WeatherGridResultadoDTO> resultados,
    Instant generatedAt,
    String source,
    int ttlSeconds
) {
}
