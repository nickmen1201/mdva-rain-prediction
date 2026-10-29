package ti.mdva.service.impl;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.MonitoreoResponseDTO;
import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.repositories.AlertaViajeRepository;
import ti.mdva.repositories.CondicionesSnapshotRepository;
import ti.mdva.service.AlertaGeneratorService;
import ti.mdva.service.WeatherMLService;
import ti.mdva.service.weather.MlApiV2Client;

import java.time.OffsetDateTime;

/**
 * Orquestador del monitoreo activo de un trayecto en curso.
 */
@Service
public class TripMonitorServiceImpl {

    private static final Logger log = LoggerFactory.getLogger(TripMonitorServiceImpl.class);

    private final CondicionesSnapshotRepository snapshotRepo;
    private final AlertaViajeRepository alertaRepo;
    private final WeatherMLService weatherMLService;
    private final MlApiV2Client mlApi;

    @Value("${monitoring.latencia.umbral-minutos:15}")
    private int latenciaUmbralMinutos;

    public TripMonitorServiceImpl(
            CondicionesSnapshotRepository snapshotRepo,
            AlertaViajeRepository alertaRepo,
            WeatherMLService weatherMLService,
            MlApiV2Client mlApi
    ) {
        this.snapshotRepo     = snapshotRepo;
        this.alertaRepo       = alertaRepo;
        this.weatherMLService = weatherMLService;
        this.mlApi            = mlApi;
    }

    /**
     * Evalúa la posición actual del conductor:
     *  1. Busca snapshot de condiciones iniciales del viaje.
     *  2. Obtiene condiciones actuales (Open-Meteo + ML API v2).
     *  3. Llama a /v2/monitor/trip (reglas RF-17) con el instante real del dato del inicio.
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

        // 3. Reglas RF-17 en el ML API (fuente única de las reglas)
        OffsetDateTime instanteDato = snapshot.timestampDatoWeather() != null
                ? snapshot.timestampDatoWeather()
                : snapshot.timestampSnapshot();
        MlApiV2Client.MonitorResult r = mlApi.monitorTrip(
                snapshot.probRfInicio() != null ? snapshot.probRfInicio() : 0.0,
                instanteDato,
                weatherMLService.currentInputs(lat, lng));

        log.info("Monitoreo viaje {}: nivel={} prob={} latencia={}",
                idViaje, r.changeLevel(), r.probabilityNow(), r.staleData());

        // 4. Generar alerta
        AlertaViajeDTO alerta = AlertaGeneratorService.generar(
            r.changeLevel(), r.probabilityNow(), r.staleData(), r.latencyMinutes(), condicionesActuales);

        if (alerta != null) {
            Integer idAlerta = alertaRepo.save(alerta, idViaje, lat, lng, r.probabilityNow(), r.staleData());
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
