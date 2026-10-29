package ti.mdva.service;

import ti.mdva.model.dto.BestWindowDTO;
import ti.mdva.model.dto.HourlyForecastDTO;

import java.time.OffsetDateTime;
import java.util.List;

/**
 * Utilitario estático que analiza una lista de predicciones horarias y devuelve
 * la mejor ventana para salir, basado en la mínima probabilidad de lluvia.
 *
 * Cubre la propuesta inicial: "Recomendaciones de horarios con menor probabilidad
 * de lluvia". Patrón TripPlannerOrchestrator (sin estado).
 *
 * Reglas:
 *   - Mejor hora = la de menor probRf en la ventana analizada
 *   - Si esa mejor hora es la primera (ahora) → salirAhora=true
 *   - Si la diferencia entre la mejor y la actual es chica (< 0.10) → salirAhora=true
 *     (porque no vale la pena esperar para una mejora marginal)
 *   - Mensaje instructivo, no sugestivo (decisión Sprint 5)
 */
public class BestWindowAnalyzer {

    private BestWindowAnalyzer() {}

    private static final double MEJORA_MINIMA_PARA_ESPERAR = 0.10; // 10 puntos

    public static BestWindowDTO analizar(List<HourlyForecastDTO> forecast) {
        if (forecast == null || forecast.isEmpty()) {
            return BestWindowDTO.builder()
                    .salirAhora(true)
                    .mensaje("No hay datos meteorológicos suficientes para recomendar un horario. Salí cuando quieras.")
                    .build();
        }

        HourlyForecastDTO actual = forecast.get(0);
        HourlyForecastDTO mejor  = forecast.stream()
                .min((a, b) -> Double.compare(probDe(a), probDe(b)))
                .orElse(actual);

        double probActual = probDe(actual);
        double probMejor  = probDe(mejor);
        double mejoraSiEspero = probActual - probMejor;
        boolean esLaActual = mejor.getTimestamp().isEqual(actual.getTimestamp());

        OffsetDateTime ahora = OffsetDateTime.now();
        int horasEspera = (int) Math.max(0,
                java.time.Duration.between(ahora, mejor.getTimestamp()).toHours());

        boolean salirAhora = esLaActual || mejoraSiEspero < MEJORA_MINIMA_PARA_ESPERAR;

        String mensaje = construirMensaje(salirAhora, probActual, probMejor, horasEspera);

        return BestWindowDTO.builder()
                .salirAhora(salirAhora)
                .mejorHora(mejor.getTimestamp())
                .probabilidadMejor(probMejor)
                .horasDeEspera(salirAhora ? 0 : horasEspera)
                .mensaje(mensaje)
                .build();
    }

    private static double probDe(HourlyForecastDTO h) {
        return h.getProbabilidadRf() != null ? h.getProbabilidadRf() : 0.0;
    }

    private static String construirMensaje(boolean salirAhora, double probActual, double probMejor, int horasEspera) {
        int pctActual = (int) Math.round(probActual * 100);
        int pctMejor  = (int) Math.round(probMejor * 100);

        if (salirAhora) {
            if (probActual < 0.30) return "Salí ahora. Las próximas horas no traen mejora significativa y la probabilidad de lluvia es baja (" + pctActual + "%).";
            if (probActual < 0.60) return "Podés salir ahora con precaución (" + pctActual + "% de lluvia). Esperar no mejora mucho.";
            return "Las condiciones no van a mejorar en las próximas horas (" + pctActual + "%). Si tenés que salir, llevá impermeable.";
        }

        String horaTexto = horasEspera == 1 ? "1 hora" : horasEspera + " horas";
        return "Esperá " + horaTexto + " para salir. La probabilidad de lluvia baja de " + pctActual + "% a " + pctMejor + "%.";
    }
}
