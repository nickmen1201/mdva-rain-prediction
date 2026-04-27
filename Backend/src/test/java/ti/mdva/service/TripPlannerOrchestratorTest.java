package ti.mdva.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import ti.mdva.model.dto.RainPredictionDTO;
import ti.mdva.model.dto.TripResponseDTO;
import ti.mdva.model.dto.TripResponseDTO.AlertaNivel;

import static org.assertj.core.api.Assertions.assertThat;

class TripPlannerOrchestratorTest {

    private static TripResponseDTO apply(double probabilidadRf, int tiempoBaseMin, int distanciaMetros) {
        RainPredictionDTO prediccion = RainPredictionDTO.builder()
                .probabilidadRf(probabilidadRf)
                .build();
        TripResponseDTO.TripResponseDTOBuilder builder = TripResponseDTO.builder();
        TripPlannerOrchestrator.apply(builder, prediccion, tiempoBaseMin, distanciaMetros);
        return builder.build();
    }

    @Nested
    @DisplayName("Nivel de alerta según probabilidad de lluvia")
    class NivelAlerta {

        @ParameterizedTest(name = "prob={0} → VERDE")
        @ValueSource(doubles = { 0.0, 0.10, 0.39, 0.399999 })
        void probabilidadBajaProduceVerde(double prob) {
            TripResponseDTO r = apply(prob, 30, 3_000);
            assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.VERDE);
            assertThat(r.getFactorAjuste()).isEqualTo(1.0);
            assertThat(r.getSugerirRutaAlterna()).isFalse();
            assertThat(r.getRazonRutaAlterna()).isNull();
        }

        @ParameterizedTest(name = "prob={0} → AMARILLO")
        @ValueSource(doubles = { 0.40, 0.55, 0.69, 0.699999 })
        void probabilidadMediaProduceAmarillo(double prob) {
            TripResponseDTO r = apply(prob, 30, 10_000);
            assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.AMARILLO);
            assertThat(r.getFactorAjuste()).isEqualTo(1.20);
            assertThat(r.getSugerirRutaAlterna()).isFalse();
        }

        @ParameterizedTest(name = "prob={0} → ROJO")
        @ValueSource(doubles = { 0.70, 0.85, 0.99, 1.0 })
        void probabilidadAltaProduceRojo(double prob) {
            TripResponseDTO r = apply(prob, 30, 3_000);
            assertThat(r.getAlertaNivel()).isEqualTo(AlertaNivel.ROJO);
            assertThat(r.getFactorAjuste()).isEqualTo(1.35);
        }
    }

    @Nested
    @DisplayName("Cálculo de tiempo ajustado")
    class TiempoAjustado {

        @Test
        void verdeNoAlteraTiempoBase() {
            TripResponseDTO r = apply(0.10, 44, 8_000);
            assertThat(r.getTiempoEstimadoMin()).isEqualTo(44);
        }

        @Test
        void amarilloAplica20PorcientoAdicional() {
            // 30 * 1.20 = 36
            TripResponseDTO r = apply(0.50, 30, 8_000);
            assertThat(r.getTiempoEstimadoMin()).isEqualTo(36);
        }

        @Test
        void rojoAplica35PorcientoAdicional() {
            // ejemplo de la doc Sprint 3: 44 * 1.35 = 59.4 → ceil = 60
            TripResponseDTO r = apply(0.75, 44, 8_000);
            assertThat(r.getTiempoEstimadoMin()).isEqualTo(60);
        }

        @Test
        void tiempoAjustadoUsaCeilNoFloor() {
            // 10 * 1.20 = 12.0 → 12; 11 * 1.20 = 13.2 → 14
            assertThat(apply(0.50, 10, 8_000).getTiempoEstimadoMin()).isEqualTo(12);
            assertThat(apply(0.50, 11, 8_000).getTiempoEstimadoMin()).isEqualTo(14);
        }
    }

    @Nested
    @DisplayName("Sugerencia de ruta alterna")
    class RutaAlterna {

        @Test
        void rojoConRutaLargaSugiereAlterna() {
            // > 5 km y ROJO → sí sugerir
            TripResponseDTO r = apply(0.85, 30, 6_000);
            assertThat(r.getSugerirRutaAlterna()).isTrue();
            assertThat(r.getRazonRutaAlterna()).isNotBlank();
        }

        @Test
        void rojoConRutaCortaNoSugiereAlterna() {
            // <= 5 km, no tiene sentido alternativa
            TripResponseDTO r = apply(0.85, 30, 4_999);
            assertThat(r.getSugerirRutaAlterna()).isFalse();
            assertThat(r.getRazonRutaAlterna()).isNull();
        }

        @Test
        void rojoEnUmbralExactoDe5kmNoSugiere() {
            // límite estricto: > 5000 (no >=)
            TripResponseDTO r = apply(0.85, 30, 5_000);
            assertThat(r.getSugerirRutaAlterna()).isFalse();
        }

        @Test
        void amarilloConRutaLargaNoSugiereAlterna() {
            // alterna solo aplica en ROJO
            TripResponseDTO r = apply(0.55, 30, 20_000);
            assertThat(r.getSugerirRutaAlterna()).isFalse();
        }
    }

    @Nested
    @DisplayName("Mensaje y propagación de la predicción")
    class Mensaje {

        @Test
        void todosLosNivelesProduceMensaje() {
            assertThat(apply(0.10, 30, 3_000).getAlertaMensaje()).isNotBlank();
            assertThat(apply(0.50, 30, 3_000).getAlertaMensaje()).isNotBlank();
            assertThat(apply(0.85, 30, 3_000).getAlertaMensaje()).isNotBlank();
        }

        @Test
        void mensajeRojoIncluyeProbabilidad() {
            // 75% probabilidad → mensaje debe contener "75"
            String msg = apply(0.75, 30, 3_000).getAlertaMensaje();
            assertThat(msg).contains("75");
        }

        @Test
        void prediccionSePropagaAlResponse() {
            RainPredictionDTO pred = RainPredictionDTO.builder()
                    .probabilidadRf(0.5)
                    .temperaturaC(20.0)
                    .humedadPct(80.0)
                    .build();
            TripResponseDTO.TripResponseDTOBuilder builder = TripResponseDTO.builder();
            TripPlannerOrchestrator.apply(builder, pred, 30, 3_000);
            TripResponseDTO r = builder.build();

            assertThat(r.getPrediccionLluvia()).isSameAs(pred);
        }
    }
}
