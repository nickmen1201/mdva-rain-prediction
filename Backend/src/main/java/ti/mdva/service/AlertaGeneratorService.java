package ti.mdva.service;

import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.RainPredictionDTO;

import java.time.OffsetDateTime;
import java.time.temporal.ChronoUnit;

/**
 * Genera una AlertaViajeDTO dado el nivel de cambio climático analizado por el ML.
 * Clase utilitaria estática, sin estado — misma filosofía que TripPlannerOrchestrator.
 */
public class AlertaGeneratorService {

    private AlertaGeneratorService() {}

    /**
     * @param nivelCambio  "ESTABLE" | "MODERADO" | "SIGNIFICATIVO" | "CRITICO"
     * @param probRfActual  Probabilidad actual del modelo RF
     * @param conLatencia   Si el dato climático tiene latencia
     * @param minutosLatencia Minutos de retraso (puede ser null)
     * @param condicionesActuales Para construir el DTO
     * @return AlertaViajeDTO, o null si no hay alerta que generar
     */
    public static AlertaViajeDTO generar(
            String nivelCambio,
            double probRfActual,
            boolean conLatencia,
            Integer minutosLatencia,
            RainPredictionDTO condicionesActuales
    ) {
        if ("ESTABLE".equals(nivelCambio) && !conLatencia) {
            return null; // No hay alerta
        }

        int probPct = (int) Math.round(probRfActual * 100);
        String notaLatencia = conLatencia
            ? " Los datos pueden tener un retraso de " + (minutosLatencia != null ? minutosLatencia : 15) + " min."
            : "";

        return switch (nivelCambio) {
            case "ESTABLE" -> // conLatencia = true
                AlertaViajeDTO.builder()
                    .tipoAlerta("DATO_DESACTUALIZADO")
                    .nivelSeveridad("INFORMATIVA")
                    .accionSugerida("CONTINUAR")
                    .mensaje("Condiciones climáticas favorables, continuar trayecto")
                    .detalleRecomendacion("Las condiciones son estables." + notaLatencia)
                    .datoConLatencia(true)
                    .timestampGeneracion(OffsetDateTime.now())
                    .build();

            case "MODERADO" ->
                AlertaViajeDTO.builder()
                    .tipoAlerta("CONDICION_CLIMATICA")
                    .nivelSeveridad("INFORMATIVA")
                    .accionSugerida("CONTINUAR")
                    .mensaje("Condiciones climáticas favorables, continuar trayecto")
                    .detalleRecomendacion("Probabilidad de lluvia: " + probPct + "%. Conduce con precaución." + notaLatencia)
                    .datoConLatencia(conLatencia)
                    .timestampGeneracion(OffsetDateTime.now())
                    .build();

            case "SIGNIFICATIVO" -> {
                boolean probable = probRfActual > 0.6;
                yield AlertaViajeDTO.builder()
                    .tipoAlerta(probable ? "CONDICION_CLIMATICA" : "CONDICION_CLIMATICA")
                    .nivelSeveridad("PELIGRO")
                    .accionSugerida(probable ? "FENOMENO_POSIBLE" : "NUEVA_RUTA")
                    .mensaje(probable
                        ? "Fenómeno climático posible en tu zona"
                        : "Nueva ruta a considerar")
                    .detalleRecomendacion("Probabilidad de lluvia intensa subió a " + probPct + "%." + notaLatencia)
                    .datoConLatencia(conLatencia)
                    .timestampGeneracion(OffsetDateTime.now())
                    .build();
            }

            default -> // CRITICO
                AlertaViajeDTO.builder()
                    .tipoAlerta("CRISIS_PUBLICA")
                    .nivelSeveridad("CRISIS")
                    .accionSugerida("CANCELAR_VIAJE")
                    .mensaje("SE RECOMIENDA CANCELAR VIAJE")
                    .detalleRecomendacion("Probabilidad crítica (" + probPct + "%). Considera detenerte en un lugar seguro." + notaLatencia)
                    .datoConLatencia(conLatencia)
                    .timestampGeneracion(OffsetDateTime.now())
                    .build();
        };
    }
}
