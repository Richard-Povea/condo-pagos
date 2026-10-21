from typing import Any

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtGui import QBrush, QColor, QFont

from condo_pagos.ui.components.tabla_base import BaseTableModel
from condo_pagos.ui.formatters import fmt_clp, fmt_fecha


class PagosTableModel(BaseTableModel):
    def __init__(self, pagos: list[Any]) -> None:
        headers = [
            "Folio", 
            "Fecha", 
            "Unidad", 
            "Pagador", 
            "Monto", 
            "Método", 
            "Estado"]
        
        datos = []
        for p in pagos:
            datos.append([
                p.folio,
                fmt_fecha(p.fecha),
                p.unidad,
                p.pagador,
                fmt_clp(p.monto),
                p.metodo,
                p.estado
            ])
        
        # Alinear a la derecha la columna de Monto (índice 4)
        super().__init__(headers, datos, alinear_derecha={4})
        self._pagos_raw = pagos

    # Actualización de la firma para aceptar QPersistentModelIndex | None
    def data(
            self, 
            index: QModelIndex | QPersistentModelIndex | None, 
            role: int = Qt.ItemDataRole.DisplayRole
            ) -> Any | None:
        if not index or not index.isValid():
            return None

        fila = index.row()
        if fila >= len(self._pagos_raw):
            return None

        pago = self._pagos_raw[fila]
        es_anulado = pago.estado.lower() == "anulado"

        # Rol de color y fuente para filas anuladas (tachadas y en gris)
        if role == Qt.ItemDataRole.ForegroundRole and es_anulado:
            return QBrush(QColor("#9FA6B2"))
            
        if role == Qt.ItemDataRole.FontRole and es_anulado:
            font = QFont()
            font.setStrikeOut(True)
            return font

        return super().data(index, role)