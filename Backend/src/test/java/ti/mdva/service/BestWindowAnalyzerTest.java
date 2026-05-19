package ti.mdva.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import ti.mdva.model.dto.BestWindowDTO;
import ti.mdva.model.dto.HourlyForecastDTO;

import java.time.OffsetDateTime;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

class BestWindowAnalyzerTest {

    private static HourlyForecastDTO h(int horasDesdeAhora, double prob) {
        return HourlyForecastDTO.builder()
                .timestamp(OffsetDateTime.now().plusHours(horasDesdeAhora))
                .hora(OffsetDateTime.now().plusHours(horasDesdeAhora).getHour())
                .probabilidadRf(prob)
                .build();
    }

    @Nested
    @DisplayName("Casos límite")
    class CasosLimite {

        @Test
        void listaVaciaDevuelveSalirAhoraConMensajeNeutral() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of());
            assertThat(r.getSalirAhora()).isTrue();
            assertThat(r.getMensaje()).contains("No hay datos");
        }

        @Test
        void listaNullDevuelveSalirAhoraConMensajeNeutral() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(null);
            assertThat(r.getSalirAhora()).isTrue();
        }

        @Test
        void unaSolaHoraSiempreEsSalirAhora() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(h(0, 0.5)));
            assertThat(r.getSalirAhora()).isTrue();
            assertThat(r.getHorasDeEspera()).isZero();
        }
    }

    @Nested
    @DisplayName("Recomienda esperar cuando hay mejora ≥ 10%")
    class Esperar {

        @Test
        void mejoraSignificativaEnHora3RecomiendaEsperar() {
            // ahora 70%, en 3h cae a 20% → mejora 50% → esperar
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(
                    h(0, 0.70), h(1, 0.65), h(2, 0.45), h(3, 0.20), h(4, 0.25)
            ));
            assertThat(r.getSalirAhora()).isFalse();
            assertThat(r.getHorasDeEspera()).isBetween(2, 4);
            assertThat(r.getMensaje()).containsIgnoringCase("esperá");
            assertThat(r.getMensaje()).contains("70%");
            assertThat(r.getMensaje()).contains("20%");
        }

        @Test
        void mensajeIncluyeProbabilidades() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(
                    h(0, 0.80), h(1, 0.30)
            ));
            assertThat(r.getProbabilidadMejor()).isEqualTo(0.30);
        }
    }

    @Nested
    @DisplayName("Recomienda salir ahora cuando la mejora es marginal o no hay mejora")
    class SalirAhora {

        @Test
        void sinMejoraSignificativaSugiereSalir() {
            // ahora 30%, las próximas son similares → mejora marginal → salir
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(
                    h(0, 0.30), h(1, 0.28), h(2, 0.27), h(3, 0.25)
            ));
            assertThat(r.getSalirAhora()).isTrue();
        }

        @Test
        void laHoraActualYaEsLaMejorRecomiendaSalirAhora() {
            // ahora 10% (mínimo), después sube → ¡salir ya!
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(
                    h(0, 0.10), h(1, 0.40), h(2, 0.70)
            ));
            assertThat(r.getSalirAhora()).isTrue();
            assertThat(r.getMensaje()).containsAnyOf("baja", "salí");
        }

        @Test
        void todoEsAltoSugiereSalirConPrecaucion() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(
                    h(0, 0.85), h(1, 0.90), h(2, 0.88)
            ));
            assertThat(r.getSalirAhora()).isTrue();
            assertThat(r.getMensaje()).containsIgnoringCase("impermeable");
        }
    }

    @Nested
    @DisplayName("Mensajes accionables (KR1: comprensión)")
    class Mensajes {

        @Test
        void mensajeProbBajaEsClaro() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(h(0, 0.15)));
            assertThat(r.getMensaje()).containsIgnoringCase("baja");
        }

        @Test
        void mensajeProbMediaEsClaro() {
            BestWindowDTO r = BestWindowAnalyzer.analizar(List.of(h(0, 0.50)));
            assertThat(r.getMensaje()).containsIgnoringCase("precaución");
        }
    }
}
