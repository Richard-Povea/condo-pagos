# src/condo_pagos/ui/services/navegacion.py
from collections.abc import Callable


class ServicioNavegacion:
    def __init__(self, callback_ir: Callable[[str, dict | None], None]) -> None:
        self._callback_ir = callback_ir

    def ir_a(self, ruta: str, params: dict | None = None) -> None:
        self._callback_ir(ruta, params)