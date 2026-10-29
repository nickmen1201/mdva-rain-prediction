package ti.mdva.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

class GoogleApiErrorTranslatorTest {

    @Nested
    @DisplayName("ZERO_RESULTS — distinto mensaje según contexto")
    class ZeroResults {

        @Test
        void enGeocodingMencionaDireccion() {
            String msg = GoogleApiErrorTranslator.traducir("ZERO_RESULTS", true);
            assertThat(msg).containsIgnoringCase("dirección");
        }

        @Test
        void enRoutingMencionaRuta() {
            String msg = GoogleApiErrorTranslator.traducir("ZERO_RESULTS", false);
            assertThat(msg).containsIgnoringCase("ruta");
            assertThat(msg).containsIgnoringCase("origen");
        }
    }

    @Nested
    @DisplayName("Mapeo a mensajes accionables (KR1)")
    class Mapeo {

        @Test
        void notFoundEsClaro() {
            String msg = GoogleApiErrorTranslator.traducir("NOT_FOUND", false);
            assertThat(msg).containsIgnoringCase("no fue reconocida");
        }

        @Test
        void overQueryLimitSugiereReintento() {
            String msg = GoogleApiErrorTranslator.traducir("OVER_QUERY_LIMIT", false);
            assertThat(msg).containsIgnoringCase("intenta de nuevo");
        }

        @Test
        void overDailyLimitMismaCategoriaQueOverQuery() {
            String a = GoogleApiErrorTranslator.traducir("OVER_DAILY_LIMIT", false);
            String b = GoogleApiErrorTranslator.traducir("OVER_QUERY_LIMIT", false);
            assertThat(a).isEqualTo(b);
        }

        @Test
        void maxWaypointsMencionaLimiteCorrecto() {
            String msg = GoogleApiErrorTranslator.traducir("MAX_WAYPOINTS_EXCEEDED", false);
            assertThat(msg).contains("5");
        }

        @Test
        void requestDeniedSugiereReportar() {
            String msg = GoogleApiErrorTranslator.traducir("REQUEST_DENIED", false);
            assertThat(msg).containsIgnoringCase("equipo");
        }
    }

    @Nested
    @DisplayName("Status desconocido")
    class Desconocido {

        @Test
        void incluyeStatusCrudoEnElMensaje() {
            String msg = GoogleApiErrorTranslator.traducir("WEIRD_NEW_STATUS_2026", false);
            assertThat(msg).contains("WEIRD_NEW_STATUS_2026");
        }

        @Test
        void distinguePrefijoPorContexto() {
            String geo  = GoogleApiErrorTranslator.traducir("X", true);
            String dir  = GoogleApiErrorTranslator.traducir("X", false);
            assertThat(geo).contains("geocodificar");
            assertThat(dir).contains("calcular la ruta");
        }
    }
}
