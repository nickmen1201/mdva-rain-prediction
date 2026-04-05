package ti.mdva.usecases;

import org.springframework.stereotype.Service;
import ti.mdva.model.valueobjects.Placa;
import ti.mdva.interfaces.IUsuarioRepository;
import ti.mdva.interfaces.IVehiculoRepository;
import ti.mdva.jooq.tables.pojos.Vehiculos;

import java.time.Year;

/**
 * UseCase para las operaciones de vehículo.
 * La validación de placa se delega al value object Placa,
 * que encapsula los patrones regex y las reglas por tipo de vehículo.
 */
@Service
public class VehiculoUseCase {

    private final IVehiculoRepository vehiculoRepository;
    private final IUsuarioRepository  usuarioRepository;

    public VehiculoUseCase(
            IVehiculoRepository vehiculoRepository,
            IUsuarioRepository usuarioRepository
    ) {
        this.vehiculoRepository = vehiculoRepository;
        this.usuarioRepository  = usuarioRepository;
    }

    /**
     * Registra un nuevo vehículo.
     *
     * - placa es PK y debe cumplir el formato colombiano para su tipo.
     * - El usuario propietario debe existir.
     * - La placa debe ser única en el sistema.
     * - El año debe estar entre 1900 y el año actual + 1.
     */
    public Vehiculos registrarVehiculo(
            String placa,
            Integer idUsuario,
            Short idTipoVehiculo,
            Short idMotorizacion,
            String marca,
            String modelo,
            Short ano
    ) {
        // Placa.of() lanza IllegalArgumentException si el formato no es válido.
        // El valor normalizado (mayúsculas, sin guiones) queda encapsulado en el VO.
        Placa placaValidada = Placa.of(placa, idTipoVehiculo);

        if (vehiculoRepository.existsByPlaca(placaValidada.valor())) {
            throw new IllegalArgumentException(
                "Ya existe un vehículo registrado con la placa '" + placaValidada.valor() + "'."
            );
        }

        usuarioRepository.findById(idUsuario.longValue())
                .orElseThrow(() -> new IllegalArgumentException(
                    "No se encontró un usuario con id: " + idUsuario
                ));

        int currentYear = Year.now().getValue();
        if (ano < 1900 || ano > currentYear + 1) {
            throw new IllegalArgumentException(
                "El año del vehículo debe estar entre 1900 y " + (currentYear + 1) + "."
            );
        }

        Vehiculos nuevoVehiculo = new Vehiculos();
        nuevoVehiculo.setPlaca(placaValidada.valor());
        nuevoVehiculo.setIdUsuario(idUsuario);
        nuevoVehiculo.setIdTipoVehiculo(idTipoVehiculo);
        nuevoVehiculo.setIdMotorizacion(idMotorizacion);
        nuevoVehiculo.setMarca(marca);
        nuevoVehiculo.setModelo(modelo);
        nuevoVehiculo.setAno(ano);

        return vehiculoRepository.save(nuevoVehiculo);
    }
}