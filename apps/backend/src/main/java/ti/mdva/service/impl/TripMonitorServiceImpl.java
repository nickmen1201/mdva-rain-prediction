package ti.mdva.service.impl;

import com.fasterxml.jackson.databind.JsonNode;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.repositories.CondicionesSnapshotRepository;
import ti.mdva.service.AlertaGeneratorService;
import ti.mdva.service.WeatherMLService;

import java.time.OffsetDateTime;
import java.util.Map;

/**
 * Orquestador del monitoreo activo de un trayecto en curso.
 */
@Service
public class TripMonitorServiceImpl {

    private static final Logger log = LoggerFactory.getLogger(TripMonitorServiceImpl.class);

    private final CondicionesSnapshotRepository snapshotRepo;
    private final AlertaViajeRepository alertaRepo;
    private final WeatherMLService weatherMLService;
    private final RestTemplate restTemplate;
    private final String mlServiceUrl;

    @Value("${monitoring.latencia.umbral-minutos:15}")
    private int latenciaUmbralMinutos;

    public TripMonitorServiceImpl(
            CondicionesSnapshotRepository snapshotRepo,
            AlertaViajeRepository alertaRepo,
            WeatherMLService weatherMLService,
            @Value("${ml.service.url}") String mlServiceUrl
    ) {
        this.snapshotRepo    = snapshotRepo;
        this.alertaRepo      = alertaRepo;
        this.weatherMLService = weatherMLService;
        this.restTemplate    = new RestTemplate();
        this.mlServiceUrl    = mlServiceUrl;
    }

    /**
     * Evalúa la posición actual del conductor:
     *  1. Busca snapshot de condiciones iniciales del viaje.
     *  2. Obtiene condiciones actuales (Google Weather + ML).
     *  3. Llama a FastAPI /monitorear/trayecto para calcular nivel_cambio.
     *  4. Genera alerta si corresponde y la persiste.
     *  5. Retorna la respuesta al frontend.
     */
    public MonitoreoResponseDTO evaluarPosicion(int idViaje, double lat, double lng) {

        // 1. Snapshot inicial
        var snapshotOpt = snapshotRepo.findByViajeId(idViaje);
        if (snapshotOpt.isEmpty()) {
            log.warn("No hay snapshot para viaje {}. Retornando solo condiciones actuales.", idViaje);
            RainPredictionDTO condiciones = weatherMLService.predictRainForLocation(lat, lng);
            return MonitoreoResponseDTO.builder().condicionesActuales(condiciones).build();
        }
        var snapshot = snapshotOpt.get();

        // 2. Condiciones actuales
        RainPredictionDTO condicionesActuales = weatherMLService.predictRainForLocation(lat, lng);

        // 3. Llamar a FastAPI /monitorear/trayecto
        // El cálculo de latencia se hace en el ML service usando timestamp_dato_weather;
        // aquí solo armamos el payload.
        OffsetDateTime now = OffsetDateTime.now();

        Map<String, Object> payload = Map.of(
            "snapshot", Map.of(
                "probabilidad_rf_inicio", snapshot.probRfInicio() != null ? snapshot.probRfInicio() : 0.0,
                "temperatura_inicio",     snapshot.temperaturaInicio() != null ? snapshot.temperaturaInicio() : 20.0,
                "timestamp_snapshot",     snapshot.timestampSnapshot().toString(),
                "timestamp_dato_weather", snapshot.timestampDatoWeather() != null ? snapshot.timestampDatoWeather().toString() : snapshot.timestampSnapshot().toString()
            ),
            "condiciones_actuales", Map.of(
                "temperatura_c",         condicionesActuales.getTemperaturaC(),
                "humedad_relativa_pct",  condicionesActuales.getHumedadPct(),
                "cobertura_nubosa_pct",  condicionesActuales.getCoberturaAnubosaPct(),
                "velocidad_viento_ms",   condicionesActuales.getVelocidadVientoMs(),
                "hora",                  now.getHour(),
                "mes",                   now.getMonthValue()
            )
        );

        String url = mlServiceUrl + "/monitorear/trayecto";
        ResponseEntity<JsonNode> mlResp = restTemplate.postForEntity(url, payload, JsonNode.class);
        JsonNode mlBody = mlResp.getBody();

        if (mlBody == null) {
            log.warn("ML /monitorear/trayecto no respondió para viaje {}", idViaje);
            return MonitoreoResponseDTO.builder().condicionesActuales(condicionesActuales).build();
        }

        String  nivelCambio    = mlBody.path("nivel_cambio").asText("ESTABLE");
        double  probRfActual   = mlBody.path("probabilidad_rf_actual").asDouble(condicionesActuales.getProbabilidadRf());
        boolean conLatencia    = mlBody.path("dato_con_latencia").asBoolean(false);
        Integer minutosLatencia = mlBody.has("minutos_latencia") ? mlBody.path("minutos_latencia").asInt() : null;

        log.info("Monitoreo viaje {}: nivel={} probRF={} latencia={}", idViaje, nivelCambio, probRfActual, conLatencia);

        // 4. Generar alerta
        AlertaViajeDTO alerta = AlertaGeneratorService.generar(
            nivelCambio, probRfActual, conLatencia, minutosLatencia, condicionesActuales);

        if (alerta != null) {
            Integer idAlerta = alertaRepo.save(alerta, idViaje, lat, lng, probRfActual, conLatencia);
            alerta = alerta.toBuilder().idAlerta(idAlerta).build();
            log.info("Alerta persistida id={} nivel={} para viaje {}", idAlerta, alerta.getNivelSeveridad(), idViaje);
        }

        // 5. Responder
        return MonitoreoResponseDTO.builder()
            .alertaNueva(alerta)
            .condicionesActuales(condicionesActuales)
            .build();
    }
}
