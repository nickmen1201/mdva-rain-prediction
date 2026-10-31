package ti.mdva.service.routing;

import ti.mdva.model.dto.LocationPointDTO;

import java.util.ArrayList;
import java.util.List;

/**
 * Orden de paradas de mínima distancia en línea recta (origen y destino fijos), por búsqueda
 * exhaustiva. Reemplaza la optimización del proveedor anterior (spec 008, research R3).
 */
public final class StopOrderOptimizer {

    /** Con 8 paradas hay 40 320 permutaciones: unos milisegundos. */
    public static final int MAX_PARADAS = 8;

    private static final double RADIO_TIERRA_M = 6_371_000;

    private StopOrderOptimizer() {}

    /**
     * Índices de {@code paradas} en el orden óptimo.
     *
     * @throws IllegalArgumentException si hay más de {@link #MAX_PARADAS} paradas
     */
    public static List<Integer> optimalOrder(LocationPointDTO origen, LocationPointDTO destino,
                                             List<LocationPointDTO> paradas) {
        int n = paradas.size();
        if (n > MAX_PARADAS) {
            throw new IllegalArgumentException(
                    "Optimizar el orden admite hasta %d paradas (se recibieron %d).".formatted(MAX_PARADAS, n));
        }
        int[] actual = new int[n];
        for (int i = 0; i < n; i++) actual[i] = i;
        int[] mejor = actual.clone();
        double mejorDist = Double.POSITIVE_INFINITY;

        // Heap's algorithm (iterativo): recorre las n! permutaciones
        int[] c = new int[n];
        mejorDist = evaluar(actual, origen, destino, paradas, mejorDist, mejor);
        int i = 0;
        while (i < n) {
            if (c[i] < i) {
                int j = (i % 2 == 0) ? 0 : c[i];
                int tmp = actual[j];
                actual[j] = actual[i];
                actual[i] = tmp;
                mejorDist = evaluar(actual, origen, destino, paradas, mejorDist, mejor);
                c[i]++;
                i = 0;
            } else {
                c[i] = 0;
                i++;
            }
        }
        List<Integer> out = new ArrayList<>(n);
        for (int idx : mejor) out.add(idx);
        return out;
    }

    private static double evaluar(int[] orden, LocationPointDTO origen, LocationPointDTO destino,
                                  List<LocationPointDTO> paradas, double mejorDist, int[] mejor) {
        double d = 0;
        LocationPointDTO prev = origen;
        for (int idx : orden) {
            d += haversine(prev, paradas.get(idx));
            prev = paradas.get(idx);
        }
        d += haversine(prev, destino);
        // Estrictamente menor: ante empate se conserva el orden ingresado (la primera permutación)
        if (d < mejorDist - 1e-9) {
            System.arraycopy(orden, 0, mejor, 0, orden.length);
            return d;
        }
        return mejorDist;
    }

    static double haversine(LocationPointDTO a, LocationPointDTO b) {
        double dLat = Math.toRadians(b.getLat() - a.getLat());
        double dLng = Math.toRadians(b.getLng() - a.getLng());
        double h = Math.pow(Math.sin(dLat / 2), 2)
                + Math.cos(Math.toRadians(a.getLat())) * Math.cos(Math.toRadians(b.getLat()))
                * Math.pow(Math.sin(dLng / 2), 2);
        return 2 * RADIO_TIERRA_M * Math.asin(Math.sqrt(h));
    }
}
