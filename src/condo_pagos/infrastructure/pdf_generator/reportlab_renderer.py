import io

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from condo_pagos.domain.comprobante import ComprobanteData


class ReportLabPdfRenderer:
    """Implementación de PdfRenderer usando ReportLab. 
    Trabaja estrictamente con el snapshot (ComprobanteData) sin consultas a BD."""

    def renderizar(
        self, comprobante: ComprobanteData, *, unidad_codigo: str | None = None
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        
        # Estilos personalizados soportando caracteres especiales (tildes y ñ)
        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#1a365d'),
            alignment=1,  # Centrado
        )
        
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#4a5568'),
            alignment=1,
        )

        heading_style = ParagraphStyle(
            'SectionHeading',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=16,
            textColor=colors.HexColor('#2b6cb0'),
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            'Body',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=colors.HexColor('#2d3748'),
        )

        bold_body_style = ParagraphStyle(
            'BoldBody',
            parent=body_style,
            fontName='Helvetica-Bold',
        )

        story = []

        # --- ENCABEZADO ---
        story.append(Paragraph("COMPROBANTE DE PAGO - GASTOS COMUNES", title_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Folio: <b>{comprobante.folio}</b>", subtitle_style))
        story.append(Spacer(1, 12))

        # --- DATOS GENERALES ---
        fecha_emision = comprobante.fecha_emision.strftime('%d-%m-%Y %H:%M')
        datos_generales_data = [
            [
                Paragraph(f"<b>Fecha de Emisión:</b> {fecha_emision}", body_style),
                Paragraph(
                    f"<b>Unidad:</b> {unidad_codigo or comprobante.unidad_id}", body_style
                ),
            ],
            [
                Paragraph(f"<b>Pagador:</b> {comprobante.residente_nombre}", body_style),
                Paragraph(f"<b>Método de Pago:</b> {comprobante.metodo_pago}", body_style),
            ],
        ]

        t_gen = Table(datos_generales_data, colWidths=[270, 270])
        t_gen.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f7fafc')),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, -1), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ]))
        story.append(t_gen)
        story.append(Spacer(1, 14))

        # --- DESGLOSE DE PAGOS POR PERÍODO / CONCEPTO ---
        story.append(Paragraph("Detalle de Aplicación del Pago", heading_style))

        detalles_data = [
            [
                Paragraph("<b>Período / Concepto</b>", bold_body_style),
                Paragraph("<b>Monto Aplicado</b>", bold_body_style),
            ]
        ]

        # Iterar sobre las asignaciones del snapshot
        for item in comprobante.lineas:
            detalles_data.append([
                Paragraph(f"Período: {item.periodo}", body_style),
                Paragraph(f"${item.monto_aplicado:,.2f}", body_style),
            ])

        t_det = Table(detalles_data, colWidths=[380, 160])
        t_det.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#edf2f7')),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_det)
        story.append(Spacer(1, 10))

        # --- RESUMEN FINANCIERO ---
        monto_pagado = comprobante.monto_pagado
        exceso_val = comprobante.exceso
        resumen_data = [
            [
                Paragraph("<b>Monto Pagado:</b>", body_style),
                Paragraph(f"${monto_pagado:,.2f}", body_style)
            ],
            [
                Paragraph("<b>Exceso Generado:</b>", body_style),
                Paragraph(f"${exceso_val:,.2f}", body_style)
            ],
        ]
        t_res = Table(resumen_data, colWidths=[380, 160])
        t_res.setStyle(TableStyle([
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_res)
        story.append(Spacer(1, 15))

        # --- QR Y HASH DE SEGURIDAD ---
        # Generar código QR en memoria con la info clave del comprobante
        folio = comprobante.folio
        hash = comprobante.hash_sha256()[:16]
        qr_data = f"Folio: {folio} | Monto: {monto_pagado} | Hash: {hash}"
        qr = qrcode.QRCode(box_size=2, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        qr_io = io.BytesIO()
        img_qr.save(qr_io, "PNG")  # 'PNG' como argumento posicional
        qr_io.seek(0)
        
        rl_qr = RLImage(qr_io, width=60, height=60)

        hash_corto = comprobante.hash_sha256()
        footer_data = [
            [
                rl_qr,
                Paragraph(
                    f"<b>Hash de Integridad SHA-256 (Verificación):</b><br/>"
                    f"<font size=7 color='#718096'>{hash_corto}</font>",
                    body_style
                ),
            ]
        ]
        t_foot = Table(footer_data, colWidths=[70, 470])
        t_foot.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_foot)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()