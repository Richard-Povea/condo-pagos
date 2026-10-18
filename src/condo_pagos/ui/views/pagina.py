# src/condo_pagos/ui/views/pagina.py
from typing import Protocol, Any

class Pagina(Protocol):
    def al_mostrar(self, parametros: Any | None) -> None:
        """Método llamado por el shell al mostrar la pantalla."""
        ...