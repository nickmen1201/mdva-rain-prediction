package ti.mdva.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

/**
 * Data Transfer Object for weather response data.
 *
 * @author MDVA Team
 * @version 1.0
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(description = "Weather data response")
public class WeatherResponseDTO {

    @Schema(description = "Latitude of the queried location")
    private Double latitude;

    @Schema(description = "Longitude of the queried location")
    private Double longitude;

    @Schema(description = "Timestamp when the data was retrieved")
    private LocalDateTime timestamp;

    @Schema(description = "Current weather conditions")
    private CurrentWeather current;

    @Schema(description = "Hourly forecast for the next 24 hours")
    private List<HourlyForecast> hourlyForecast;

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class CurrentWeather {
        private Double temperature;
        private Double feelsLike;
        private Integer relativeHumidity;
        private Double precipitation;
        private Integer rainProbability;
        private Double windSpeed;
        private Integer windDirection;
        private String description;
        private RiskLevel riskLevel;
    }

    @Data
    @Builder
    @NoArgsConstructor
    @AllArgsConstructor
    public static class HourlyForecast {
        private LocalDateTime time;
        private Double temperature;
        private Integer rainProbability;
        private Double precipitation;
        private RiskLevel riskLevel;
    }

    public enum RiskLevel {
        LOW, MODERATE, HIGH, VERY_HIGH
    }
}
