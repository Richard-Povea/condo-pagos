# src/condo_pagos/ui/services/interfaces.py
from pathlib import Path
from typing import Protocol


class IServicioDialogos(Protocol):
    def confirmar(self, titulo: str, texto: str, peligro: bool = False) -> bool:
        ...

class IAbridorArchivos(Protocol):
    def abrir(self, ruta: Path | str) -> None:
        ...