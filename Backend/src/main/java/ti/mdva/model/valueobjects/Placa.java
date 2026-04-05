package ti.mdva.model.valueobjects;

import java.util.regex.Pattern;

/**
 * Value object que representa una placa vehicular colombiana.
 *
 * Encapsula el valor y las reglas de formato según la normativa vigente:
 *
 *   Autos / camionetas / buses / camiones:   3 letras + 3 dígitos      (ej: ABC123)
 *   Motos (formato clásico):                 3 letras + 2 dígitos + 1 letra (ej: ABC12D)
 *   Motos (formato nuevo, desde ~2018):      3 letras + 3 dígitos      (ej: ABC123)
 *   Diplomáticas:                            2 letras + 4 dígitos      (ej: CD1234)
 *   Bicicletas:                              sin placa — siempre válidas
 *
 * El objeto es inmutable. Se instancia únicamente a través de Placa.of(...)
 * que lanza IllegalArgumentException si el formato no es válido.
 *
 * Uso:
 *   Placa placa = Placa.of("ABC123", (short) 4);
 *   String valor = placa.valor(); // "ABC123"
 */
public final class Placa {

    // ── Patrones (prefijo PATRON_ para evitar colisión con las constantes del enum) ──

    private static final Pattern PATRON_AUTO         = Pattern.compile("^[A-Z]{3}\\d{3}$");
    private static final Pattern PATRON_MOTO_CLASICA = Pattern.compile("^[A-Z]{3}\\d{2}[A-Z]$");
    private static final Pattern PATRON_DIPLOMATICA  = Pattern.compile("^[A-Z]{2}\\d{4}$");

    // ── Estado ────────────────────────────────────────────────────────────────

    private final String valor;

    private Placa(String valor) {
        this.valor = valor;
    }

    // ── Factory ───────────────────────────────────────────────────────────────

    /**
     * Crea y valida una Placa para el tipo de vehículo dado.
     *
     * @param rawPlaca       placa en cualquier capitalización, guiones y espacios opcionales
     * @param idTipoVehiculo ID del tipo de vehículo (ver tabla tipos_vehiculo)
     * @return Placa válida
     * @throws IllegalArgumentException si el formato no coincide con el tipo
     */
    public static Placa of(String rawPlaca, Short idTipoVehiculo) {
        if (rawPlaca == null || rawPlaca.isBlank()) {
            throw new IllegalArgumentException("La placa no puede estar vacía.");
        }

        String limpia = rawPlaca.toUpperCase().replaceAll("[\\-\\s]", "");
        TipoCategoria categoria = TipoCategoria.fromId(idTipoVehiculo);

        if (!categoria.esValida(limpia)) {
            throw new IllegalArgumentException(String.format(
                "La placa '%s' no es válida para %s. %s",
                rawPlaca,
                categoria.descripcion(),
                categoria.formatoEsperado()
            ));
        }

        return new Placa(limpia);
    }

    /**
     * Valida sin lanzar excepción. Útil para pre-validaciones en capa de presentación.
     */
    public static boolean esValida(String rawPlaca, Short idTipoVehiculo) {
        if (rawPlaca == null || rawPlaca.isBlank()) return false;
        try {
            of(rawPlaca, idTipoVehiculo);
            return true;
        } catch (IllegalArgumentException e) {
            return false;
        }
    }

    // ── Valor ─────────────────────────────────────────────────────────────────

    /** Retorna la placa normalizada (mayúsculas, sin guiones ni espacios). */
    public String valor() {
        return valor;
    }

    @Override
    public String toString() {
        return valor;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof Placa other)) return false;
        return valor.equals(other.valor);
    }

    @Override
    public int hashCode() {
        return valor.hashCode();
    }

    // ── Enum interno de categorías ────────────────────────────────────────────

    /**
     * Categorías de vehículo con su lógica de validación.
     * Los IDs corresponden a la tabla tipos_vehiculo de la BD.
     *
     * NOTA: las constantes del enum (BICICLETA, MOTO, AUTO_MOTO) se nombran
     * distintas a los Pattern de la clase externa para evitar colisión de nombres.
     */
    private enum TipoCategoria {

        BICICLETA {
            @Override public boolean esValida(String p)    { return true; }
            @Override public String  descripcion()         { return "Bicicleta / Bicicleta eléctrica"; }
            @Override public String  formatoEsperado()     { return "Las bicicletas no requieren placa."; }
        },

        MOTO {
            @Override public boolean esValida(String p) {
                // Acepta formato clásico (ABC12D) y formato nuevo (ABC123)
                return PATRON_MOTO_CLASICA.matcher(p).matches()
                    || PATRON_AUTO.matcher(p).matches();
            }
            @Override public String descripcion()      { return "Motocicleta"; }
            @Override public String formatoEsperado()  {
                return "Formato esperado: 3 letras + 2 dígitos + 1 letra (ej: ABC12D) "
                     + "o 3 letras + 3 dígitos (ej: ABC123).";
            }
        },

        VEHICULO_MOTOR {
            @Override public boolean esValida(String p) {
                return PATRON_AUTO.matcher(p).matches()
                    || PATRON_DIPLOMATICA.matcher(p).matches();
            }
            @Override public String descripcion()      { return "Automóvil / Camioneta / Bus / Camión"; }
            @Override public String formatoEsperado()  {
                return "Formato esperado: 3 letras + 3 dígitos (ej: ABC123) "
                     + "o 2 letras + 4 dígitos para diplomáticas (ej: CD1234).";
            }
        };

        public abstract boolean esValida(String placaNormalizada);
        public abstract String  descripcion();
        public abstract String  formatoEsperado();

        /**
         * Mapea el idTipoVehiculo de la BD a una categoría.
         *
         *   1–2   → BICICLETA
         *   3     → MOTO
         *   4–11  → VEHICULO_MOTOR (automóvil, taxi, camioneta, SUV, van, camión, bus, tractocamión)
         */
        static TipoCategoria fromId(Short id) {
            if (id == null) {
                throw new IllegalArgumentException("El tipo de vehículo no puede ser nulo.");
            }
            return switch (id) {
                case 1, 2                          -> BICICLETA;
                case 3                             -> MOTO;
                case 4, 5, 6, 7, 8, 9, 10, 11     -> VEHICULO_MOTOR;
                default -> throw new IllegalArgumentException(
                    "Tipo de vehículo desconocido: " + id
                );
            };
        }
    }
}