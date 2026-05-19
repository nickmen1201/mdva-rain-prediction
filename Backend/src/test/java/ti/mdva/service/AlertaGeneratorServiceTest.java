package ti.mdva.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import ti.mdva.model.dto.AlertaViajeDTO;
import ti.mdva.model.dto.RainPredictionDTO;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Tests para la rúbrica de alertas del Sprint 5.2A:
 * los textos exactos al usuario son criterio KR1 (comprensión) y NO se deben parafrasear.
 */
class AlertaGeneratorServiceTest {

    private static final RainPredictionDTO COND = RainPredictionDTO.builder()
            .probabilidadRf(0.5)
            .temperaturaC(20.0)
            .humedadPct(75.0)
            .build();

    @Nested
    @DisplayName("ESTABLE")
    class Estable {

        @Test
        void sinLatenciaNoGeneraAlerta() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("ESTABLE", 0.2, false, null, COND);
            assertThat(a).isNull();
        }

        @Test
        void conLatenciaGeneraAlertaInformativa() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("ESTABLE", 0.2, true, 18, COND);
            assertThat(a).isNotNull();
            assertThat(a.getNivelSeveridad()).isEqualTo("INFORMATIVA");
            assertThat(a.getAccionSugerida()).isEqualTo("CONTINUAR");
            assertThat(a.getMensaje()).isEqualTo("Condiciones climáticas favorables, continuar trayecto");
            assertThat(a.getDatoConLatencia()).isTrue();
            assertThat(a.getDetalleRecomendacion()).contains("18 min");
        }
    }

    @Nested
    @DisplayName("MODERADO")
    class Moderado {

        @Test
        void textoExactoYNivelInformativa() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("MODERADO", 0.45, false, null, COND);
            assertThat(a.getNivelSeveridad()).isEqualTo("INFORMATIVA");
            assertThat(a.getAccionSugerida()).isEqualTo("CONTINUAR");
            assertThat(a.getMensaje()).isEqualTo("Condiciones climáticas favorables, continuar trayecto");
            assertThat(a.getDetalleRecomendacion()).contains("45%");
        }
    }

    @Nested
    @DisplayName("SIGNIFICATIVO")
    class Significativo {

        @Test
        void probMenor60UsaMensajeNuevaRuta() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("SIGNIFICATIVO", 0.55, false, null, COND);
            assertThat(a.getNivelSeveridad()).isEqualTo("PELIGRO");
            assertThat(a.getAccionSugerida()).isEqualTo("NUEVA_RUTA");
            assertThat(a.getMensaje()).isEqualTo("Nueva ruta a considerar");
            assertThat(a.getTipoAlerta()).isEqualTo("CONDICION_CLIMATICA");
        }

        @Test
        void probMayor60UsaMensajeFenomenoPosible() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("SIGNIFICATIVO", 0.75, false, null, COND);
            assertThat(a.getNivelSeveridad()).isEqualTo("PELIGRO");
            assertThat(a.getAccionSugerida()).isEqualTo("FENOMENO_POSIBLE");
            assertThat(a.getMensaje()).isEqualTo("Fenómeno climático posible en tu zona");
            assertThat(a.getTipoAlerta()).isEqualTo("FENOMENO_PROBABLE");
        }
    }

    @Nested
    @DisplayName("CRITICO")
    class Critico {

        @Test
        void textoExactoCancelacionYNivelCrisis() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("CRITICO", 0.92, false, null, COND);
            assertThat(a.getNivelSeveridad()).isEqualTo("CRISIS");
            assertThat(a.getAccionSugerida()).isEqualTo("CANCELAR_VIAJE");
            assertThat(a.getMensaje()).isEqualTo("SE RECOMIENDA CANCELAR VIAJE");
            assertThat(a.getTipoAlerta()).isEqualTo("CRISIS_PUBLICA");
        }

        @Test
        void incluyeProbabilidadEnDetalle() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("CRITICO", 0.92, false, null, COND);
            assertThat(a.getDetalleRecomendacion()).contains("92%");
        }
    }

    @Nested
    @DisplayName("Latencia")
    class Latencia {

        @Test
        void notaLatenciaSeAgregaCuandoConLatencia() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("MODERADO", 0.5, true, 22, COND);
            assertThat(a.getDetalleRecomendacion()).contains("22 min");
            assertThat(a.getDatoConLatencia()).isTrue();
        }

        @Test
        void notaLatenciaUsaDefault15CuandoMinutosNull() {
            AlertaViajeDTO a = AlertaGeneratorService.generar("MODERADO", 0.5, true, null, COND);
            assertThat(a.getDetalleRecomendacion()).contains("15 min");
        }
    }
}
