from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from condo_pagos.domain.errors import MontoInvalidoError


def cuantizar(valor: Decimal) -> Decimal:
    """Cuantiza un valor decimal a enteros estrictos (el peso chileno no usa decimales)."""
    return valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def parsear_monto(valor_str: str | int | Decimal) -> Decimal:
    """Parsea un monto monetario en pesos chilenos (CLP), validando restricciones estrictas:

    - Rechaza tipos float puros.
    - Rechaza montos menores o iguales a cero.
    - Limpia separadores de miles (puntos) comunes en formato chileno (ej. '125.000').
    - Exige que el resultado sea un número entero (sin decimales).
    """
    if isinstance(valor_str, float):
        raise MontoInvalidoError(
            "No se permiten tipos float para montos monetarios debido a pérdida de precisión."
        )

    if isinstance(valor_str, int):
        decimal_val = Decimal(valor_str)
    elif isinstance(valor_str, Decimal):
        decimal_val = valor_str
    elif isinstance(valor_str, str):
        limpio = valor_str.strip()
        if not limpio:
            raise MontoInvalidoError("El monto no puede estar vacío.")
        
        # Limpiar símbolo de peso, espacios y puntos de miles (formato chileno)
        limpio = limpio.replace("$", "").replace(" ", "").replace(".", "")
        
        # Si por error ingresaron comas como decimales, las rechazamos o advertimos
        if "," in limpio:
            raise MontoInvalidoError("El peso chileno no admite valores decimales.")

        try:
            decimal_val = Decimal(limpio)
        except InvalidOperation as e:
            raise MontoInvalidoError(f"Formato de monto inválido: '{valor_str}'") from e
    else:
        raise MontoInvalidoError(f"Tipo de dato no soportado para montos: {type(valor_str)}")

    if decimal_val <= Decimal("0"):
        raise MontoInvalidoError("El monto debe ser mayor estrictamente a cero.")

    # Asegurar que no tenga parte fraccionaria
    cuantizado = cuantizar(decimal_val)
    if decimal_val != cuantizado:
        raise MontoInvalidoError("El monto en pesos chilenos no puede tener decimales.")

    return cuantizado