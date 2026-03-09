package ti.mdva.service;

/**
 * Servicio responsable de validar formatos de placa según el tipo de vehículo colombiano.
 */
public interface ValidadorPlacasService {

    /**
     * Valida si una placa es correcta para un tipo de vehículo específico.
     *
     * @param placa          Placa (puede contener guiones o espacios, se limpian automáticamente)
     * @param idTipoVehiculo ID del tipo de vehículo según la tabla id_tipo_vehiculo
     * @return true si la placa es válida para ese tipo de vehículo
     * @throws IllegalArgumentException si el idTipoVehiculo no existe o la placa es inválida
     */
    boolean esPlacaValida(String placa, Short idTipoVehiculo);

    /**
     * Valida la placa y lanza excepción con mensaje claro si no es válida.
     * Ideal para usar directamente en los Use Cases.
     */
    void validarPlaca(String placa, Short idTipoVehiculo);
}