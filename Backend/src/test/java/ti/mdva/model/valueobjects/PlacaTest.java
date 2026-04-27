package ti.mdva.model.valueobjects;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class PlacaTest {

    // IDs según mapeo en Placa.TipoCategoria.fromId
    private static final short ID_BICICLETA      = 1;
    private static final short ID_BICICLETA_ELEC = 2;
    private static final short ID_MOTO           = 3;
    private static final short ID_AUTO           = 4;
    private static final short ID_CAMION         = 10;
    private static final short ID_TIPO_INVALIDO  = 99;

    @Nested
    @DisplayName("Vehículos de motor (autos, camiones, etc.)")
    class VehiculosMotor {

        @ParameterizedTest(name = "placa válida: \"{0}\"")
        @ValueSource(strings = { "ABC123", "abc123", "ABC-123", " ABC 123 ", "CD1234" })
        void aceptaFormatosValidos(String entrada) {
            Placa p = Placa.of(entrada, ID_AUTO);
            assertThat(p.valor()).matches("^[A-Z]{2,3}\\d{3,4}$");
        }

        @Test
        void normalizaAMayusculasYSinSeparadores() {
            assertThat(Placa.of("abc-123", ID_AUTO).valor()).isEqualTo("ABC123");
            assertThat(Placa.of(" ab 123 4 ", ID_AUTO).valor()).isEqualTo("AB1234");
        }

        @ParameterizedTest(name = "placa inválida: \"{0}\"")
        @ValueSource(strings = { "AB123", "ABCD123", "ABC12", "ABC1234", "12ABCD", "ABC12D" })
        void rechazaFormatosInvalidos(String entrada) {
            assertThatThrownBy(() -> Placa.of(entrada, ID_AUTO))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining(entrada);
        }

        @Test
        void aceptaMismoFormatoParaCualquierIdEntre4y11() {
            // El comportamiento debe ser consistente para autos, taxis, vans, camiones, buses, etc.
            for (short id = 4; id <= 11; id++) {
                assertThat(Placa.of("XYZ987", id).valor()).isEqualTo("XYZ987");
            }
        }
    }

    @Nested
    @DisplayName("Motocicletas")
    class Motocicletas {

        @ParameterizedTest(name = "moto formato clásico: \"{0}\"")
        @ValueSource(strings = { "ABC12D", "abc12d", "ABC-12D" })
        void aceptaFormatoClasico(String entrada) {
            Placa p = Placa.of(entrada, ID_MOTO);
            assertThat(p.valor()).matches("^[A-Z]{3}\\d{2}[A-Z]$");
        }

        @ParameterizedTest(name = "moto formato nuevo: \"{0}\"")
        @ValueSource(strings = { "ABC123", "XYZ999" })
        void aceptaFormatoNuevo(String entrada) {
            Placa p = Placa.of(entrada, ID_MOTO);
            assertThat(p.valor()).matches("^[A-Z]{3}\\d{3}$");
        }

        @ParameterizedTest(name = "moto inválida: \"{0}\"")
        @ValueSource(strings = { "AB12D", "ABCD12D", "ABC1D", "1234567" })
        void rechazaFormatosInvalidos(String entrada) {
            assertThatThrownBy(() -> Placa.of(entrada, ID_MOTO))
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Nested
    @DisplayName("Bicicletas (no requieren placa)")
    class Bicicletas {

        @ParameterizedTest(name = "bicicleta acepta: \"{0}\"")
        @ValueSource(strings = { "X", "12345", "no-aplica", "ABC123", "qwerty" })
        void aceptaCualquierValorNoVacio(String entrada) {
            // Las bicicletas no requieren placa: cualquier valor (no vacío ni nulo) es válido
            Placa pBici = Placa.of(entrada, ID_BICICLETA);
            Placa pBiciElec = Placa.of(entrada, ID_BICICLETA_ELEC);
            assertThat(pBici).isNotNull();
            assertThat(pBiciElec).isNotNull();
        }

        @Test
        void rechazaPlacaVaciaIncluyendoBicicleta() {
            // El check de "vacía/nula" se aplica antes de la categoría
            assertThatThrownBy(() -> Placa.of("", ID_BICICLETA))
                    .isInstanceOf(IllegalArgumentException.class);
            assertThatThrownBy(() -> Placa.of("   ", ID_BICICLETA))
                    .isInstanceOf(IllegalArgumentException.class);
        }
    }

    @Nested
    @DisplayName("Validación de entrada")
    class EntradaInvalida {

        @ParameterizedTest
        @NullAndEmptySource
        @ValueSource(strings = { "   ", "\t" })
        void rechazaPlacaNulaOVacia(String entrada) {
            assertThatThrownBy(() -> Placa.of(entrada, ID_AUTO))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContainingAll("placa");
        }

        @Test
        void rechazaTipoVehiculoNulo() {
            assertThatThrownBy(() -> Placa.of("ABC123", null))
                    .isInstanceOf(IllegalArgumentException.class);
        }

        @Test
        void rechazaTipoVehiculoDesconocido() {
            assertThatThrownBy(() -> Placa.of("ABC123", ID_TIPO_INVALIDO))
                    .isInstanceOf(IllegalArgumentException.class)
                    .hasMessageContaining("99");
        }
    }

    @Nested
    @DisplayName("API esValida (no-throw)")
    class EsValida {

        @Test
        void retornaTrueParaPlacaValida() {
            assertThat(Placa.esValida("ABC123", ID_AUTO)).isTrue();
        }

        @Test
        void retornaFalseParaPlacaInvalidaSinLanzar() {
            assertThat(Placa.esValida("AB123", ID_AUTO)).isFalse();
            assertThat(Placa.esValida(null, ID_AUTO)).isFalse();
            assertThat(Placa.esValida("", ID_AUTO)).isFalse();
        }
    }

    @Nested
    @DisplayName("Identidad del value object")
    class Identidad {

        @Test
        void dosPlacasConMismoValorSonIguales() {
            Placa a = Placa.of("ABC123", ID_AUTO);
            Placa b = Placa.of("abc-123", ID_AUTO);
            assertThat(a).isEqualTo(b);
            assertThat(a.hashCode()).isEqualTo(b.hashCode());
        }

        @Test
        void toStringDevuelveValorNormalizado() {
            assertThat(Placa.of("abc-123", ID_AUTO)).hasToString("ABC123");
        }
    }
}
