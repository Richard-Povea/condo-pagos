from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from condo_pagos.domain.comprobante import ComprobanteData, LineaCargo
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.infrastructure.storage.filesystem_storage import FileSystemStorage


def main():
    print("Generando comprobante de prueba...")
    
    # 1. Crear datos de prueba
    comprobante = ComprobanteData(
        folio="2026-000001",
        fecha_emision=date(2026, 10, 12),
        unidad_id=uuid4(),
        residente_nombre="María José Muñoz",
        monto_pagado=Decimal("50000"),
        metodo_pago="TRANSFERENCIA",
        lineas=(
            LineaCargo(
                cargo_id=uuid4(),
                periodo="2026-09",
                monto_original=Decimal("50000"),
                saldo_restante=Decimal("0"),
                monto_aplicado=Decimal("50000")
            ),
        ),
        exceso=Decimal("0"),
        hash_anterior=None,
    )

    # 2. Renderizar a bytes
    renderer = ReportLabPdfRenderer()
    pdf_bytes = renderer.renderizar(comprobante)

    # 3. Guardar en una carpeta local 'output_debug' para abrirlo
    storage = FileSystemStorage(base_dir=Path("output_debug"))
    ruta_relativa = storage.guardar(comprobante.folio, pdf_bytes)

    archivo_final = Path("output_debug") / ruta_relativa
    print("¡PDF generado con éxito!")
    print(f"Ruta del archivo: {archivo_final.resolve()}")

if __name__ == "__main__":
    main()