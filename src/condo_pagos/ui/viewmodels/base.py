from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QThreadPool, Signal, Slot

from condo_pagos.ui.workers import Worker


class BaseViewModel(QObject):
    ocupado_cambio = Signal(bool)
    error = Signal(str)

    def __init__(self, pool: QThreadPool | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = pool or QThreadPool.globalInstance()
        self._pendientes: dict[str, tuple[Worker, Callable[[Any], None]]] = {}

    @property
    def ocupado(self) -> bool:
        return bool(self._pendientes)

    def _ejecutar(self, fn: Callable[..., Any], *args: Any, on_ok: Callable[[object], None]) -> None:
        w = Worker(fn, *args)
        w.signals.ok.connect(self._cuando_ok)
        w.signals.fail.connect(self._cuando_fail)
        self._pendientes[w.id] = (w, on_ok)
        self.ocupado_cambio.emit(True)
        self._pool.start(w)

    @Slot(str, object)
    def _cuando_ok(self, wid: str, res: Any) -> None:
        _, on_ok = self._pendientes.pop(wid)
        self.ocupado_cambio.emit(self.ocupado)
        on_ok(res)

    @Slot(str, str)
    def _cuando_fail(self, wid: str, msg: str) -> None:
        self._pendientes.pop(wid, None)
        self.ocupado_cambio.emit(self.ocupado)
        self.error.emit(msg)