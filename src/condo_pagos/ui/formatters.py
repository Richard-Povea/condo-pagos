# src/condo_pagos/ui/formatters.py
from datetime import date
from decimal import Decimal

def fmt_clp(valor: Decimal | int | float) -> str:
    """Formatea montos monetarios en pesos chilenos (ej: $125.000)."""
    if isinstance(valor, float):
        valor = Decimal(str(valor))
    elif isinstance(valor, int):
        valor = Decimal(valor)
    
    # Formato con separador de miles usando puntos
    entero = int(valor)
    return f"${entero:,}".replace(",", ".")

def fmt_fecha(f: date | None) -> str:
    """Formatea fechas al estandar dd-mm-aaaa."""
    if not f:
        return ""
    return f.strftime("%d-%m-%Y")

def fmt_folio(prefijo: str, numero: int) -> str:
    """Genera el formato estándar de folio."""
    return f"{prefijo}-{numero:06d}"