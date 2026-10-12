# src/condo_pagos/ui/services/interfaces.py
from typing import Protocol
from pathlib import Path

class IServicioDialogos(Protocol):
    def confirmar(self, titulo: str, texto: str, peligro: bool = False) -> bool:
        ...

class IAbridorArchivos(Protocol):
    def abrir(self, ruta: Path | str) -> None:
        ...