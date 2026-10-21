from collections.abc import Callable
from typing import Any
from datetime import date

from PySide6.QtCore import Signal

from condo_pagos.ui.viewmodels.base import BaseViewModel


class PagosViewModel(BaseViewModel):
    # Señales
    pagos_cargados = Signal(list, int)        # (lista_pagos, total_paginas)
    pago_anulado = Signal(str)                # folio del pago anulado
    comprobante_abierto = Signal(str)         # ruta del PDF abierto

    def __init__(
            self, 
            listar_pagos_uc: Callable[..., Any],
            emitir_pdf_uc: Callable[..., Any],
            anular_pago_uc: Callable[..., Any],
            abridor_archivos: Any,
            parent: Any | None = None) -> None:
        super().__init__(parent=parent)
        self._listar_uc = listar_pagos_uc
        self._emitir_pdf_uc = emitir_pdf_uc
        self._anular_uc = anular_pago_uc
        self._abridor = abridor_archivos

        # Filtros activos y paginación
        self.pagina_actual: int = 1
        self.limite_por_pagina: int = 50
        self.filtro_texto: str = ""
        self.filtro_metodo: str | None = None
        self.filtro_estado: str | None = None
        self.fecha_desde: date | None = None
        self.fecha_hasta: date | None = None

    def cargar_pagos(self) -> None:
        """Carga la página actual de pagos aplicando los filtros combinados."""
        def tarea() -> Any:
            filtros = {
                "texto": self.filtro_texto,
                "metodo": self.filtro_metodo,
                "estado": self.filtro_estado,
                "fecha_desde": self.fecha_desde,
                "fecha_hasta": self.fecha_hasta,
            }
            return self._listar_uc(
                filtros=filtros, 
                pagina=self.pagina_actual, 
                limite=self.limite_por_pagina
                )

        def on_ok(resultado: Any) -> None:
            if resultado:
                self.pagos_cargados.emit(resultado.filas, resultado.total_paginas)
            else:
                self.pagos_cargados.emit([], 0)

        self._ejecutar(tarea, on_ok=on_ok)

    def abrir_o_reimprimir_comprobante(
            self, 
            comprobante_id: str, 
            ruta_actual_disco: str | None
            ) -> None:
        """Abre el PDF existente o lo reimprime de forma idempotente si falta."""
        def tarea() -> Any:
            from pathlib import Path
            if ruta_actual_disco and Path(ruta_actual_disco).exists():
                return ruta_actual_disco
            # Si no existe, solicitamos al backend la reimpresión desde el snapshot
            return self._emitir_pdf_uc(comprobante_id)

        def on_ok(ruta_pdf: Any) -> None:
            self._abridor.abrir(ruta_pdf)
            self.comprobante_abierto.emit(str(ruta_pdf))

        self._ejecutar(tarea, on_ok=on_ok)

    def anular_pago(self, pago_id: str, motivo: str, operador: str) -> None:
        """Anula un pago exigiendo un motivo válido y revirtiendo saldos en el backend."""
        if len(motivo.strip()) < 10:
            raise ValueError("El motivo de anulación debe tener al menos 10 caracteres.")

        def tarea():
            return self._anular_uc(pago_id=pago_id, motivo=motivo, operador=operador)

        def on_ok(folio: str) -> None:
            self.pago_anulado.emit(folio)
            self.cargar_pagos()  # Refrescar listado

        self._ejecutar(tarea, on_ok=on_ok)