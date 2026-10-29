package ti.mdva.service;

import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.TripResponseDTO;
import ti.mdva.model.dto.TripResponseDTO.AlertaNivel;

/**
 * Orquesta la lógica de negocio que combina la ruta de Google con la predicción ML.
 *
 * Reglas de ajuste de tiempo por lluvia:
 *
 *   probabilidad RF < 40%   → VERDE    · sin ajuste     (factor 1.00)
 *   probabilidad RF 40–70%  → AMARILLO · tiempo +20%    (factor 1.20)
 *   probabilidad RF > 70%   → ROJO     · tiempo +35%,   (factor 1.35)
 *                                         sugerir ruta alterna
 *
 * La sugerencia de ruta alterna se activa adicionalmente cuando:
 *   - probRf > 70%  Y  distancia > 5 km
 *   (rutas cortas no se benefician de tomar alternativas en lluvia intensa)
 */
public class TripPlannerOrchestrator {

    private static final double UMBRAL_AMARILLO = 0.40;
    private static final double UMBRAL_ROJO     = 0.70;
    private static final double FACTOR_AMARILLO = 1.20;
    private static final double FACTOR_ROJO     = 1.35;
    private static final int    DISTANCIA_ALTERNA_METROS = 5_000;

    private TripPlannerOrchestrator() {}

    /**
     * Aplica las reglas de ajuste sobre un TripResponseDTO parcialmente construido.
     * Muta el builder in-place y retorna la misma referencia.
     *
     * @param builder   builder de TripResponseDTO con tiempoBaseMin y distanciaMetros ya seteados
     * @param prediccion resultado del modelo ML
     * @return builder enriquecido con tiempoEstimadoMin, factorAjuste, alerta y sugerencia
     */
    public static TripResponseDTO.TripResponseDTOBuilder apply(
            TripResponseDTO.TripResponseDTOBuilder builder,
            RainPredictionDTO prediccion,
            int tiempoBaseMin,
            int distanciaMetros
    ) {
        double prob = prediccion.getProbabilidadRf();

        AlertaNivel nivel;
        double factor;
        boolean sugerirAlterna = false;
        String razonAlterna    = null;
        String mensajeAlerta;

        if (prob < UMBRAL_AMARILLO) {
            nivel   = AlertaNivel.VERDE;
            factor  = 1.0;
            mensajeAlerta = "Condiciones climáticas favorables para el viaje.";

        } else if (prob < UMBRAL_ROJO) {
            nivel   = AlertaNivel.AMARILLO;
            factor  = FACTOR_AMARILLO;
            mensajeAlerta = String.format(
                "Probabilidad de lluvia moderada (%.0f%%). Tiempo estimado ajustado +20%%.",
                prob * 100
            );

        } else {
            nivel   = AlertaNivel.ROJO;
            factor  = FACTOR_ROJO;
            mensajeAlerta = String.format(
                "Alta probabilidad de lluvia (%.0f%%). Tiempo ajustado +35%%. Conduce con precaución.",
                prob * 100
            );

            if (distanciaMetros > DISTANCIA_ALTERNA_METROS) {
                sugerirAlterna = true;
                razonAlterna = String.format(
                    "Con %.0f%% de probabilidad de lluvia intensa en una ruta de %.1f km, " +
                    "considera una ruta alternativa con mejor cobertura o menos tráfico.",
                    prob * 100,
                    distanciaMetros / 1000.0
                );
            }
        }

        int tiempoAjustado = (int) Math.ceil(tiempoBaseMin * factor);

        return builder
                .tiempoEstimadoMin(tiempoAjustado)
                .factorAjuste(factor)
                .alertaNivel(nivel)
                .alertaMensaje(mensajeAlerta)
                .sugerirRutaAlterna(sugerirAlterna)
                .razonRutaAlterna(razonAlterna)
                .prediccionLluvia(prediccion);
    }
}
