package ti.mdva.service.routing;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import ti.mdva.model.dto.LocationPointDTO;

import java.util.ArrayList;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

@DisplayName("StopOrderOptimizer — orden exhaustivo de paradas (spec 008)")
class StopOrderOptimizerTest {

    private static LocationPointDTO p(double lat, double lng) {
        return LocationPointDTO.builder().lat(lat).lng(lng).build();
    }

    @Test
    @DisplayName("paradas sobre una línea norte→sur ingresadas desordenadas se ordenan de norte a sur")
    void ordenaSobreUnaLinea() {
        LocationPointDTO origen = p(6.30, -75.57);
        LocationPointDTO destino = p(6.15, -75.57);
        List<LocationPointDTO> paradas = List.of(p(6.18, -75.57), p(6.27, -75.57), p(6.22, -75.57));

        assertThat(StopOrderOptimizer.optimalOrder(origen, destino, paradas)).containsExactly(1, 2, 0);
    }

    @Test
    @DisplayName("si el orden ingresado ya es óptimo se conserva (empates incluidos)")
    void conservaOrdenOptimo() {
        LocationPointDTO origen = p(6.30, -75.57);
        LocationPointDTO destino = p(6.15, -75.57);
        List<LocationPointDTO> paradas = List.of(p(6.27, -75.57), p(6.22, -75.57));

        assertThat(StopOrderOptimizer.optimalOrder(origen, destino, paradas)).containsExactly(0, 1);
        assertThat(StopOrderOptimizer.optimalOrder(origen, destino, List.of(p(6.2, -75.5))))
                .containsExactly(0);
        assertThat(StopOrderOptimizer.optimalOrder(origen, destino, List.of())).isEmpty();
    }

    @Test
    @DisplayName("el resultado no es peor que ninguna otra permutación (8 paradas)")
    void optimoConOchoParadas() {
        LocationPointDTO origen = p(6.20, -75.60);
        LocationPointDTO destino = p(6.20, -75.50);
        List<LocationPointDTO> paradas = new ArrayList<>();
        double[][] coords = {{6.25, -75.55}, {6.15, -75.58}, {6.22, -75.52}, {6.18, -75.56},
                             {6.28, -75.59}, {6.12, -75.51}, {6.21, -75.57}, {6.26, -75.53}};
        for (double[] c : coords) paradas.add(p(c[0], c[1]));

        List<Integer> orden = StopOrderOptimizer.optimalOrder(origen, destino, paradas);

        assertThat(orden).containsExactlyInAnyOrder(0, 1, 2, 3, 4, 5, 6, 7);
        double optimo = largo(origen, destino, paradas, orden);
        assertThat(optimo).isCloseTo(minimoRecursivo(origen, destino, paradas, new ArrayList<>(), new boolean[8]),
                org.assertj.core.data.Offset.offset(1e-6));
    }

    @Test
    @DisplayName("más de 8 paradas → IllegalArgumentException (400)")
    void limite() {
        List<LocationPointDTO> nueve = new ArrayList<>();
        for (int i = 0; i < 9; i++) nueve.add(p(6.2 + i * 0.01, -75.57));

        assertThatThrownBy(() -> StopOrderOptimizer.optimalOrder(p(6.1, -75.5), p(6.4, -75.5), nueve))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("8");
    }

    @Test
    @DisplayName("haversine Parque Berrío → El Poblado ≈ 4.6 km")
    void haversine() {
        assertThat(StopOrderOptimizer.haversine(p(6.2502, -75.5684), p(6.2088, -75.5672)))
                .isBetween(4600.0, 4611.0);
    }

    /** Mínimo por recursión independiente del algoritmo de Heap usado en producción. */
    private static double minimoRecursivo(LocationPointDTO o, LocationPointDTO d, List<LocationPointDTO> ps,
                                          List<Integer> prefijo, boolean[] usado) {
        if (prefijo.size() == ps.size()) return largo(o, d, ps, prefijo);
        double min = Double.POSITIVE_INFINITY;
        for (int i = 0; i < ps.size(); i++) {
            if (usado[i]) continue;
            usado[i] = true;
            prefijo.add(i);
            min = Math.min(min, minimoRecursivo(o, d, ps, prefijo, usado));
            prefijo.remove(prefijo.size() - 1);
            usado[i] = false;
        }
        return min;
    }

    private static double largo(LocationPointDTO o, LocationPointDTO d, List<LocationPointDTO> ps, List<Integer> orden) {
        double total = 0;
        LocationPointDTO prev = o;
        for (int i : orden) {
            total += StopOrderOptimizer.haversine(prev, ps.get(i));
            prev = ps.get(i);
        }
        return total + StopOrderOptimizer.haversine(prev, d);
    }
}
