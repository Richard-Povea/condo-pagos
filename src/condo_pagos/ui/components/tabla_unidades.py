from typing import Any

from condo_pagos.ui.components.tabla_base import BaseTableModel
from condo_pagos.ui.formatters import fmt_clp


class UnidadesTableModel(BaseTableModel):
    def __init__(self, unidades: list[Any]) -> None:
        headers = ["Unidad", "Responsable", "RUT", "Saldo Total", "Estado"]
        
        # Transformar DTOs a filas planas compatibles con la tabla
        datos = []
        for u in unidades:
            estado = "Al día" if u.saldo_total <= 0 else "Moroso"
            datos.append([
                u.identificador,
                u.responsable,
                u.rut,
                fmt_clp(u.saldo_total),
                estado
            ])
        
        # Alinear a la derecha la columna de Saldo Total (índice 3)
        super().__init__(headers, datos, alinear_derecha={3})