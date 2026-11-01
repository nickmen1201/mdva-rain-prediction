package ti.mdva.controller;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;

import ti.mdva.service.geocoding.GeocodingResultDTO;
import ti.mdva.service.geocoding.NominatimClient;
import ti.mdva.service.geocoding.PhotonClient;

import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

@DisplayName("GeocodingController — búsqueda y reverso (spec 008)")
class GeocodingControllerTest {

    private final NominatimClient nominatim = mock(NominatimClient.class);
    private final PhotonClient photon = mock(PhotonClient.class);
    private final GeocodingController controller = new GeocodingController(nominatim, photon);
    private static final GeocodingResultDTO EXPLORA =
            new GeocodingResultDTO("Parque Explora, Medellín", 6.2706, -75.5658, "museum");

    @Test
    @DisplayName("search delega en Nominatim")
    void search() {
        when(nominatim.search("explora")).thenReturn(List.of(EXPLORA));
        assertThat(controller.search("explora")).containsExactly(EXPLORA);
    }

    @Test
    @DisplayName("suggest delega en Photon")
    void suggest() {
        when(photon.suggest("explo")).thenReturn(List.of(EXPLORA));
        assertThat(controller.suggest("explo")).containsExactly(EXPLORA);
    }

    @Test
    @DisplayName("reverse: 200 con resultado, 404 sin dirección")
    void reverse() {
        when(nominatim.reverse(6.2706, -75.5658)).thenReturn(Optional.of(EXPLORA));
        when(nominatim.reverse(6.0, -75.0)).thenReturn(Optional.empty());

        assertThat(controller.reverse(6.2706, -75.5658).getBody()).isEqualTo(EXPLORA);
        assertThat(controller.reverse(6.0, -75.0).getStatusCode()).isEqualTo(HttpStatus.NOT_FOUND);
    }

    @Test
    @DisplayName("reverse con coordenadas fuera de rango → 400 sin llamar a Nominatim")
    void reverseFueraDeRango() {
        assertThatThrownBy(() -> controller.reverse(91, 0)).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> controller.reverse(0, -181)).isInstanceOf(IllegalArgumentException.class);
        verifyNoInteractions(nominatim, photon);
    }
}
