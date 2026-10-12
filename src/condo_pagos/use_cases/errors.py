from condo_pagos.domain.errors import DominioError


class ErrorDeAplicacion(DominioError):
    """
    Excepción base para errores controlados de negocio y aplicación 
    que deben mostrarse de forma amigable al usuario en la UI.
    """
    pass

class ErrorDeInfraestructura(ErrorDeAplicacion):
    """
    Envuelve errores técnicos imprevistos (fallos de red, caída de BD, etc.)
    traduciéndolos a un mensaje amigable para el operador.
    """
    mensaje = "No se pudo conectar con la base de datos. Verifique la red o avise al administrador."
    def __init__(self, mensaje: str = mensaje) -> None:
        super().__init__(mensaje)