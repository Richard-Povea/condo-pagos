"""Contenedor de demostración con datos en memoria.

Este adaptador satisface las funciones que consume la UI actual sin requerir
PostgreSQL. Sus datos se reinician cada vez que se cierra la aplicación.
No debe utilizarse para producción.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@dataclass
class UnidadDemo:
    unidad_id: UUID
    identificador: str
    responsable: str
    rut: str
    saldo_total: Decimal


@dataclass
class EstadoCuentaDemo:
    unidad_id: UUID
    codigo_unidad: str
    total_adeudado: Decimal


@dataclass
class PagoDemo:
    pago_id: UUID
    folio: str
    fecha: date
    unidad: str
    pagador: str
    monto: Decimal
    metodo: str
    estado: str = "Vigente"
    referencia: str = ""


@dataclass
class ResultadoPagosDemo:
    filas: list[PagoDemo]
    total_paginas: int


class InMemoryContainer:
    """Implementación de demostración con datos ficticios y operaciones locales."""

    def __init__(self) -> None:
        self.nombre_condominio = "Condominio Los Alerces (Demo)"
        self._unidades = [
            UnidadDemo(uuid4(), "101", "María González", "12.345.678-5", Decimal("50000")),
            UnidadDemo(uuid4(), "202", "Pedro Soto", "9.876.543-2", Decimal("0")),
            UnidadDemo(uuid4(), "303", "Ana Rojas", "15.234.567-8", Decimal("82500")),
        ]
        self._pagos: list[PagoDemo] = []
        self._folios = 1

    def listar_unidades(self, solo_morosas: bool = False) -> list[UnidadDemo]:
        """Lista las unidades de muestra, opcionalmente solo las que tienen deuda."""
        if solo_morosas:
            return [u for u in self._unidades if u.saldo_total > 0]
        return list(self._unidades)

    def buscar_unidades(self, texto: str = "") -> list[UnidadDemo]:
        """Busca unidades por número, responsable o RUT."""
        criterio = texto.casefold().strip()
        if not criterio:
            return list(self._unidades)
        return [
            u for u in self._unidades
            if criterio in u.identificador.casefold()
            or criterio in u.responsable.casefold()
            or criterio in u.rut.casefold()
        ]

    def consultar_estado_cuenta(self, unidad_id: UUID | str) -> EstadoCuentaDemo:
        """Devuelve el saldo de una unidad de muestra."""
        unidad = self._obtener_unidad(unidad_id)
        return EstadoCuentaDemo(
            unidad_id=unidad.unidad_id,
            codigo_unidad=unidad.identificador,
            total_adeudado=unidad.saldo_total,
        )

    def registrar_pago(
        self,
        *,
        unidad_id: UUID | str,
        monto: Decimal | int | str,
        metodo_pago: str = "EFECTIVO",
        referencia: str = "",
        operador: str = "Demo",
        fecha: date | None = None,
        **kwargs: object,
    ) -> SimpleNamespace:
        """Registra un pago ficticio y descuenta el saldo de la unidad en memoria."""
        unidad = self._obtener_unidad(unidad_id)
        monto_decimal = Decimal(str(monto))
        if monto_decimal <= 0:
            raise ValueError("El monto debe ser mayor que cero.")
        if monto_decimal > unidad.saldo_total:
            raise ValueError("En modo demo no se permite pagar más que la deuda.")
        if referencia and any(p.referencia == referencia for p in self._pagos):
            raise ValueError("Ya existe un pago con esa referencia.")

        folio = f"DEMO-{self._folios:06d}"
        self._folios += 1
        unidad.saldo_total -= monto_decimal
        pago = PagoDemo(
            pago_id=uuid4(),
            folio=folio,
            fecha=fecha or date.today(),
            unidad=unidad.identificador,
            pagador=operador,
            monto=monto_decimal,
            metodo=metodo_pago,
            referencia=referencia,
        )
        self._pagos.insert(0, pago)
        return SimpleNamespace(folio=folio, pago_id=pago.pago_id, monto_pagado=monto_decimal)

    def listar_pagos(
        self,
        *,
        filtros: dict[str, Any] | None = None,
        pagina: int = 1,
        limite: int = 50,
    ) -> ResultadoPagosDemo:
        """Lista pagos de demostración aplicando filtros de texto y estado."""
        filtros = filtros or {}
        filas = list(self._pagos)
        texto = str(filtros.get("texto") or "").casefold().strip()
        estado = str(filtros.get("estado") or "").casefold().strip()
        metodo = str(filtros.get("metodo") or "").casefold().strip()
        desde = filtros.get("fecha_desde")
        hasta = filtros.get("fecha_hasta")

        if texto:
            filas = [
                p for p in filas
                if texto in p.folio.casefold()
                or texto in p.unidad.casefold()
                or texto in p.pagador.casefold()
            ]
        if estado:
            filas = [p for p in filas if estado in p.estado.casefold()]
        if metodo:
            filas = [p for p in filas if metodo in p.metodo.casefold()]
        if desde:
            filas = [p for p in filas if p.fecha >= desde]
        if hasta:
            filas = [p for p in filas if p.fecha <= hasta]

        total_paginas = (len(filas) + limite - 1) // limite if filas else 0
        inicio = max(pagina - 1, 0) * limite
        return ResultadoPagosDemo(filas=filas[inicio:inicio + limite], total_paginas=total_paginas)

    def emitir_pdf(self, comprobante_id: str) -> str:
        """Genera un comprobante PDF sencillo para un pago de demostración."""
        pago = next(
            (
                p for p in self._pagos
                if p.folio == comprobante_id or str(p.pago_id) == comprobante_id
                ), 
            None
            )
        if pago is None:
            raise ValueError(f"No se encontró el pago de demostración: {comprobante_id}")

        carpeta = Path.cwd() / "storage" / "demo"
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / f"comprobante_{pago.folio}.pdf"
        pdf = canvas.Canvas(str(ruta), pagesize=letter)
        pdf.setTitle(f"Comprobante {pago.folio} - Demo")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, 730, "COMPROBANTE DE PAGO - DEMOSTRACIÓN")
        pdf.setFont("Helvetica", 11)
        lineas = [
            f"Folio: {pago.folio}",
            f"Fecha: {pago.fecha:%d-%m-%Y}",
            f"Unidad: {pago.unidad}",
            f"Pagador: {pago.pagador}",
            f"Monto: $ {pago.monto:,.0f}",
            f"Método: {pago.metodo}",
            "",
            "Documento generado con datos ficticios. No es un comprobante oficial.",
        ]
        y = 690
        for linea in lineas:
            pdf.drawString(72, y, linea)
            y -= 24
        pdf.save()
        return str(ruta)

    def anular_pago(
        self,
        *,
        pago_id: str,
        motivo: str = "",
        operador: str = "Demo",
        **kwargs: object,
    ) -> str:
        """Anula un pago ficticio y restituye el saldo a la unidad."""
        pago = next(
            (
                p for p in self._pagos 
                if str(p.pago_id) == str(pago_id) or p.folio == str(pago_id)
                ), 
                None)
        if pago is None:
            raise ValueError(f"No se encontró el pago: {pago_id}")
        if pago.estado.casefold() == "anulado":
            raise ValueError("El pago ya está anulado.")
        unidad = next(u for u in self._unidades if u.identificador == pago.unidad)
        unidad.saldo_total += pago.monto
        pago.estado = "Anulado"
        return pago.folio

    def _obtener_unidad(self, unidad_id: UUID | str) -> UnidadDemo:
        try:
            buscado = unidad_id if isinstance(unidad_id, UUID) else UUID(str(unidad_id))
            unidad = next((u for u in self._unidades if u.unidad_id == buscado), None)
        except ValueError:
            unidad = next((u for u in self._unidades if u.identificador == str(unidad_id)), None)
        if unidad is None:
            raise ValueError(f"No se encontró la unidad de demostración: {unidad_id}")
        return unidad
