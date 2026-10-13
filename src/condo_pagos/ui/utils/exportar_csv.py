import csv
from pathlib import Path


def exportar_pagos_a_csv(ruta_archivo: Path | str, pagos: list) -> None:
    """Exporta el listado de pagos a CSV usando UTF-8 con BOM para compatibilidad con Excel."""
    with open(ruta_archivo, mode="w", encoding="utf-8-sig", newline="") as archivo:
        writer = csv.writer(archivo, delimiter=";")
        # Cabeceras
        writer.writerow(["Folio", "Fecha", "Unidad", "Pagador", "Monto", "Método", "Estado"])
        
        # Filas
        for p in pagos:
            writer.writerow([
                p.folio,
                p.fecha,
                p.unidad,
                p.pagador,
                p.monto,
                p.metodo,
                p.estado
            ])