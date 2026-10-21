from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Signal

from condo_pagos.ui.viewmodels.base import BaseViewModel


class UnidadesViewModel(BaseViewModel):
    # Señales
    unidades_cargadas = Signal(list)
    detalle_unidad_cargado = Signal(object)  # Estado de cuenta DTO
    navegar_a_pago = Signal(object)          # Emite la unidad para preseleccionarla

    def __init__(self, listar_unidades_uc: Callable[..., Any], consultar_estado_uc: Callable[..., Any], parent: Any | None = None) -> None:
        super().__init__(parent=parent)
        self._listar_uc = listar_unidades_uc
        self._consultar_estado_uc = consultar_estado_uc
        
        self.solo_morosas: bool = False
        self._texto_filtro: str = ""

    def cargar_unidades(self) -> None:
        """Carga el listado de unidades aplicando el filtro de morosidad."""
        def tarea() -> Any:
            return self._listar_uc(solo_morosas=self.solo_morosas)

        self._ejecutar(tarea, on_ok=lambda res: self.unidades_cargadas.emit(res))

    def seleccionar_unidad(self, unidad_id: str) -> None:
        """Consulta el estado de cuenta detallado de una unidad específica."""
        def tarea():
            return self._consultar_estado_uc(unidad_id)

        self._ejecutar(tarea, on_ok=lambda estado: self.detalle_unidad_cargado.emit(estado))

    def alternar_filtro_morosas(self, solo_morosas: bool) -> None:
        self.solo_morosas = solo_morosas
        self.cargar_unidades()

    def iniciar_pago_para_unidad(self, unidad: Any) -> None:
        """Dispara la navegación hacia Registrar Pago con la unidad seleccionada."""
        self.navegar_a_pago.emit(unidad)