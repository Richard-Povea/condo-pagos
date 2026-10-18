# src/condo_pagos/ui/services/navegacion.py
from typing import Any
from PySide6.QtCore import QObject, Signal

class ServicioNavegacion(QObject):
    navegar = Signal(str, object)  # (clave_pagina, parametros)

    def ir_a(self, clave: str, parametros: Any | None = None) -> None:
        self.navegar.emit(clave, parametros)