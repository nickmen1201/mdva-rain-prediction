class DomainException(Exception):
    pass


class RouteNotFoundError(DomainException):
    def __init__(self, message="No se pudo encontrar una ruta entre los puntos dados."):
        super().__init__(message)


class LocationOutOfBoundsError(DomainException):
    def __init__(self, message="La ubicación está fuera de los límites permitidos de Medellín."):
        super().__init__(message)
