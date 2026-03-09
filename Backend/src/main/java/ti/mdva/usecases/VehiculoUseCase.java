package ti.mdva.usecases;

import org.springframework.stereotype.Service;
import ti.mdva.jooq.tables.pojos.Vehiculos;
import ti.mdva.interfaces.IVehiculoRepository;
import ti.mdva.interfaces.IUsuarioRepository;
import ti.mdva.service.ValidadorPlacasService;   // ← Importante: aquí está el servicio

import java.time.Year;

/*
    UseCase para las operaciones de vehículo
*/
@Service
public class VehiculoUseCase {

    private final IVehiculoRepository vehiculoRepository;
    private final IUsuarioRepository usuarioRepository;
    private final ValidadorPlacasService validadorPlacasService;   // Servicio validador de placas

    public VehiculoUseCase(
            IVehiculoRepository vehiculoRepository,
            IUsuarioRepository usuarioRepository,
            ValidadorPlacasService validadorPlacasService) {   // Inyección del servicio validador de placas

        this.vehiculoRepository = vehiculoRepository;
        this.usuarioRepository = usuarioRepository;
        this.validadorPlacasService = validadorPlacasService;
    }

    // -------------------------------------------------------------------------
    // RegistrarVehiculo
    // -------------------------------------------------------------------------

    /**
     * Registers a new vehiculo.
     * - placa is the PK and must be provided — it is not auto-generated.
     * - The owning usuario must exist.
     * - placa must be unique.
     * - ano must be between 1900 and current year + 1 (mirrors DB check constraint).
     * - La placa debe cumplir el formato oficial colombiano según el tipo de vehículo.
     *
     * @param placa          license plate — acts as primary key
     * @param idUsuario      ID of the owning user
     * @param idTipoVehiculo vehicle type reference
     * @param idMotorizacion motorization type reference
     * @param marca          brand name
     * @param modelo         model name
     * @param ano            manufacture year
     * @return the persisted Vehiculo
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

        // Validación de la placa a partir del servicio dedicado
        validadorPlacasService.validarPlaca(placa, idTipoVehiculo);

        // La placa es única
        if (vehiculoRepository.existsByPlaca(placa)) {
            throw new IllegalArgumentException(
                "Ya existe un vehículo registrado con la placa '" + placa + "'."
            );
        }

        // Debe ser agregado por un usuario existente
        usuarioRepository.findById(idUsuario.longValue())
                .orElseThrow(() -> new IllegalArgumentException(
                    "No se encontró un usuario con id: " + idUsuario
                ));

        // Recibimos vehículos a partir del 1900
        int currentYear = Year.now().getValue();
        if (ano < 1900 || ano > currentYear + 1) {
            throw new IllegalArgumentException(
                "El año del vehículo debe estar entre 1900 y " + (currentYear + 1) + "."
            );
        }

        Vehiculos nuevoVehiculo = new Vehiculos();
        nuevoVehiculo.setPlaca(placa);
        nuevoVehiculo.setIdUsuario(idUsuario);
        nuevoVehiculo.setIdTipoVehiculo(idTipoVehiculo);
        nuevoVehiculo.setIdMotorizacion(idMotorizacion);
        nuevoVehiculo.setMarca(marca);
        nuevoVehiculo.setModelo(modelo);
        nuevoVehiculo.setAno(ano);

        return vehiculoRepository.save(nuevoVehiculo);
    }
}