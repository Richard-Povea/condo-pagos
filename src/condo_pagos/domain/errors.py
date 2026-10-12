class DominioError(Exception):
    """Excepción base para todos los errores de la capa de dominio."""

    def __init__(self, mensaje: str) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje


class MontoInvalidoError(DominioError):
    """Se lanza cuando el monto ingresado no cumple con el formato o reglas financieras."""

    pass


class PagoExcedeDeudaError(DominioError):
    """Se lanza cuando el pago supera la deuda total pendiente de la unidad."""

    pass


class PagoDuplicadoError(DominioError):
    """Se lanza al intentar registrar un pago idéntico ya existente."""

    pass


class UnidadInactivaError(DominioError):
    """Se lanza al intentar realizar operaciones sobre una unidad inmobiliaria inactiva."""

    pass


class PagoYaAnuladoError(DominioError):
    """Se lanza al intentar anular un pago que ya se encuentra anulado previamente."""

    pass


class PeriodoNoEmitidoError(DominioError):
    """Se lanza cuando se intenta asociar un cargo a un periodo de cobro que no ha sido emitido."""

    pass