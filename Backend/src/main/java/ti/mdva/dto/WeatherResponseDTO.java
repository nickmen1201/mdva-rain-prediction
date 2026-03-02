package ti.mdva.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * Response DTO for weather data.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class WeatherResponseDTO {
    private Double latitude;
    private Double longitude;
    private LocalDateTime timestamp;
    private Double temperature;
    private Double precipitation;
    private Double humidity;
    private Double windSpeed;
    private Integer weatherCode;
    private String weatherDescription;
}
