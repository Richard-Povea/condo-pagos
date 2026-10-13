# src/condo_pagos/ui/services/configuracion.py
import getpass

from PySide6.QtCore import QSettings


class ConfiguracionLocal:
    def __init__(self) -> None:
        self._settings = QSettings("CondoPagos", "ModuloPagos")

    @property
    def operador(self) -> str:
        # Casteo explícito a str ya que .value() retorna object
        op = str(self._settings.value("operador", ""))
        if not op:
            op = getpass.getuser()
            self.set_operador(op)
        return op

    def set_operador(self, nombre: str) -> None:
        self._settings.setValue("operador", nombre)

    @property
    def primera_ejecucion_pendiente(self) -> bool:
        return not self._settings.contains("operador")