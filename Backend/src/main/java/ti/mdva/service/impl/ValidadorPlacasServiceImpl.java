package ti.mdva.service.impl;

import org.springframework.stereotype.Service;
import ti.mdva.service.ValidadorPlacasService;

import java.util.regex.Pattern;

/**
 * Validador de placas colombianas según id_tipo_vehiculo (versión simplificada sin Map).
 */
@Service
public class ValidadorPlacasServiceImpl implements ValidadorPlacasService {

    // Patrones regex (compilados una sola vez)
    private static final Pattern PATRON_AUTO = Pattern.compile("^[A-Z]{3}\\d{3}$");
    private static final Pattern PATRON_MOTO = Pattern.compile("^[A-Z]{3}\\d{2}[A-Z]$");
    private static final Pattern PATRON_DIPLOMATICA = Pattern.compile("^[A-Z]{2}\\d{4}$");

    @Override
    public boolean esPlacaValida(String placa, Short idTipoVehiculo) {
        if (placa == null || placa.trim().isEmpty()) {
            return false;
        }

        String limpia = placa.toUpperCase().replaceAll("[-\\s]", "");

        // Determinamos la categoría con un switch simple (más seguro y sin imports extra)
        String categoria = obtenerCategoria(idTipoVehiculo);

        if (categoria == null) {
            return false; // Tipo de vehículo desconocido
        }

        return switch (categoria) {
            case "MOTO" -> PATRON_MOTO.matcher(limpia).matches() ||
                           PATRON_AUTO.matcher(limpia).matches();   // muchas motos nuevas usan formato 3+3
            case "AUTO" -> PATRON_AUTO.matcher(limpia).matches() ||
                           PATRON_DIPLOMATICA.matcher(limpia).matches();
            case "BICICLETA" -> true; // Las bicicletas no llevan placa real
            default -> false;
        };
    }

    @Override
    public void validarPlaca(String placa, Short idTipoVehiculo) {
        if (!esPlacaValida(placa, idTipoVehiculo)) {
            String nombreTipo = obtenerNombreTipo(idTipoVehiculo);
            throw new IllegalArgumentException(
                String.format("La placa '%s' NO es válida para un(a) %s (id: %d). " +
                              "Formato esperado: 3 letras + 3 números (autos) o 3 letras + 2 números + 1 letra (motos).",
                    placa, nombreTipo, idTipoVehiculo)
            );
        }
    }

    // =====================================================================
    // Métodos privados simples (sin Map ni estructuras complejas)
    // =====================================================================

    private String obtenerCategoria(Short id) {
        if (id == null) return null;

        return switch (id) {
            case 1, 2  -> "BICICLETA";
            case 3     -> "MOTO";
            case 4, 5, 6, 7, 8, 9, 10, 11 -> "AUTO";
            default    -> null;
        };
    }

    private String obtenerNombreTipo(Short id) {
        if (id == null) return "desconocido";

        return switch (id) {
            case 1  -> "Bicicleta";
            case 2  -> "Bicicleta eléctrica";
            case 3  -> "Motocicleta";
            case 4  -> "Automóvil";
            case 5  -> "Taxi";
            case 6  -> "Camioneta";
            case 7  -> "SUV";
            case 8  -> "Van";
            case 9  -> "Camión";
            case 10 -> "Bus";
            case 11 -> "Tractocamión";
            default -> "vehículo de tipo " + id;
        };
    }
}