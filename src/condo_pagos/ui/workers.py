import logging
import uuid

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from condo_pagos.use_cases.errors import ErrorDeAplicacion

log = logging.getLogger(__name__)

class _Signals(QObject):
    ok = Signal(str, object)      # (id_worker, resultado)
    fail = Signal(str, str)       # (id_worker, mensaje)

class Worker(QRunnable):
    def __init__(self, fn, *args) -> None:
        super().__init__()
        self.setAutoDelete(False) # El ViewModel decide cuándo soltarlo
        self.id = uuid.uuid4().hex
        self._fn, self._args = fn, args
        self.signals = _Signals()

    @Slot()
    def run(self) -> None:
        try:
            self.signals.ok.emit(self.id, self._fn(*self._args))
        except ErrorDeAplicacion as e:
            self.signals.fail.emit(self.id, str(e))
        except Exception:
            log.exception("Error inesperado en worker")
            self.signals.fail.emit(
                self.id, 
                "Ocurrió un problema inesperado. Revise el registro de la aplicación."
                )