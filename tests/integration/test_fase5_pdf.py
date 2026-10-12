import io
from datetime import date
from decimal import Decimal
from uuid import uuid4
import pypdf

from condo_pagos.domain.comprobante import ComprobanteData, LineaCargo
from condo_pagos.infrastructure.pdf_generator.reportlab_renderer import ReportLabPdfRenderer
from condo_pagos.infrastructure.storage.filesystem_storage import FileSystemStorage


def test_1_pdf_comienza_con_formato_correcto():
    """El PDF generado debe empezar con el magic number %PDF."""
    renderer = ReportLabPdfRenderer()
    
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

    pdf_bytes = renderer.renderizar(comprobante)
    
    # Verificar bytes iniciales
    assert pdf_bytes.startswith(b"%PDF")


def test_2_extraccion_texto_con_pypdf():
    """Con pypdf se extrae el texto y se verifica folio, unidad, montos y tildes/ñ."""
    renderer = ReportLabPdfRenderer()
    unidad_id = uuid4()
    
    comprobante = ComprobanteData(
        folio="2026-000002",
        fecha_emision=date(2026, 10, 12),
        unidad_id=unidad_id,
        residente_nombre="Ñusta Pérez",
        monto_pagado=Decimal("75000"),
        metodo_pago="TRANSFERENCIA",
        lineas=(
                LineaCargo(
                    cargo_id=uuid4(), 
                    periodo="2026-09", 
                    monto_original=Decimal("75000"),
                    saldo_restante=Decimal("0"),
                    monto_aplicado=Decimal("75000")
                ),
            ),
        exceso=Decimal("0"),
        hash_anterior=None,
    )

    pdf_bytes = renderer.renderizar(comprobante)
    
    # Leer con pypdf desde BytesIO
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    texto_extraido = ""
    for page in reader.pages:
        texto_extraido += page.extract_text() or ""

    assert "2026-000002" in texto_extraido
    assert str(unidad_id) in texto_extraido
    assert "75,000.00" in texto_extraido or "75000" in texto_extraido
    assert "Ñusta Pérez" in texto_extraido
    assert comprobante.hash_sha256()[:16] in texto_extraido


def test_3_almacenamiento_atomico_filesystem(tmp_path):
    """Verifica que el almacenamiento atómico cree la carpeta por año y guarde el archivo."""
    # Apuntamos directamente a tmp_path para que base_dir sea la raíz del almacenamiento
    storage = FileSystemStorage(base_dir=tmp_path)
    
    folio = "2026-000003"
    contenido = b"%PDF-1.4 mock content"
    
    ruta_relativa = storage.guardar(folio, contenido)
    
    # La ruta absoluta se construye uniendo tmp_path con la ruta relativa retornada
    ruta_absoluta = tmp_path / ruta_relativa
    assert ruta_absoluta.exists()
    assert ruta_absoluta.read_bytes() == contenido
    assert "2026" in str(ruta_absoluta)