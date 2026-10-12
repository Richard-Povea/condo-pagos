import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from condo_pagos.domain.money import cuantizar


@dataclass(frozen=True)
class LineaCargo:
    cargo_id: UUID
    periodo: str
    monto_original: Decimal
    monto_aplicado: Decimal
    saldo_restante: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "cargo_id": str(self.cargo_id),
            "periodo": self.periodo,
            "monto_original": str(self.monto_original),
            "monto_aplicado": str(self.monto_aplicado),
            "saldo_restante": str(self.saldo_restante),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LineaCargo":
        return cls(
            cargo_id=UUID(data["cargo_id"]),
            periodo=data["periodo"],
            monto_original=Decimal(data["monto_original"]),
            monto_aplicado=Decimal(data["monto_aplicado"]),
            saldo_restante=Decimal(data["saldo_restante"]),
        )


@dataclass(frozen=True)
class ComprobanteData:
    folio: str
    fecha_emision: date
    unidad_id: UUID
    residente_nombre: str
    monto_pagado: Decimal
    metodo_pago: str
    lineas: tuple[LineaCargo, ...]
    exceso: Decimal
    hash_anterior: str | None = None

    def __post_init__(self) -> None:
        # Asegurar normalización de montos
        object.__setattr__(self, "monto_pagado", cuantizar(self.monto_pagado))
        object.__setattr__(self, "exceso", cuantizar(self.exceso))

    def a_dict(self) -> dict[str, Any]:
        """Convierte los datos del comprobante a un diccionario ordenado y serializable."""
        return {
            "folio": self.folio,
            "fecha_emision": self.fecha_emision.isoformat(),
            "unidad_id": str(self.unidad_id),
            "residente_nombre": self.residente_nombre,
            "monto_pagado": str(self.monto_pagado),
            "metodo_pago": self.metodo_pago,
            "lineas": [linea.to_dict() for linea in self.lineas],
            "exceso": str(self.exceso),
            "hash_anterior": self.hash_anterior,
        }

    def a_json(self) -> str:
        """Serializa la estructura a JSON con claves ordenadas (sort_keys=True) 
        para garantizar determinismo en el hash.
        """
        return json.dumps(self.a_dict(), sort_keys=True, ensure_ascii=False)

    @classmethod
    def desde_json(cls, json_str: str) -> "ComprobanteData":
        """Reconstruye el ComprobanteData desde una cadena JSON, 
        transformando strings de vuelta a Decimal, date, UUID y tuplas.
        """
        data = json.loads(json_str)
        
        lineas_reconstruidas = tuple(
            LineaCargo.from_dict(linea) for linea in data.get("lineas", [])
        )

        return cls(
            folio=data["folio"],
            fecha_emision=date.fromisoformat(data["fecha_emision"]),
            unidad_id=UUID(data["unidad_id"]),
            residente_nombre=data["residente_nombre"],
            monto_pagado=Decimal(data["monto_pagado"]),
            metodo_pago=data["metodo_pago"],
            lineas=lineas_reconstruidas,
            exceso=Decimal(data["exceso"]),
            hash_anterior=data.get("hash_anterior"),
        )

    def hash_sha256(self) -> str:
        """Calcula el hash SHA-256 criptográfico de integridad 
        basado en su representación JSON canónica."""
        contenido_canonico = self.a_json().encode("utf-8")
        return hashlib.sha256(contenido_canonico).hexdigest()