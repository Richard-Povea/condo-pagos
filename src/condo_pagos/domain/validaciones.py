"""Validaciones puras de datos de dominio."""

from condo_pagos.domain.errors import (
    MotivoAnulacionInvalidoError,
    OperadorInvalidoError,
    ReferenciaInvalidaError,
)


def normalizar_referencia(referencia: str | None) -> str | None:
    """Recorta una referencia opcional y valida su longitud máxima."""
    limpia = (referencia or "").strip() or None
    if limpia is not None and len(limpia) > 100:
        raise ReferenciaInvalidaError("La referencia no puede superar los 100 caracteres.")
    return limpia


def validar_operador(operador: str | None) -> str:
    """Devuelve el operador normalizado, de 1 a 80 caracteres."""
    limpio = (operador or "").strip()
    if not limpio:
        raise OperadorInvalidoError("Debe indicar un operador válido.")
    if len(limpio) > 80:
        raise OperadorInvalidoError("El operador no puede superar los 80 caracteres.")
    return limpio


def validar_motivo(motivo: str | None) -> str:
    """Devuelve el motivo normalizado, de 10 a 300 caracteres."""
    limpio = (motivo or "").strip()
    if len(limpio) < 10:
        raise MotivoAnulacionInvalidoError(
            "El motivo de anulación debe tener al menos 10 caracteres."
        )
    if len(limpio) > 300:
        raise MotivoAnulacionInvalidoError(
            "El motivo de anulación no puede superar los 300 caracteres."
        )
    return limpio
