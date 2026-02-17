# apps/documentos/services/pdf_compra.py
"""
📦 GENERADOR PDF - ORDEN DE COMPRA
====================================

Genera PDF oficial de compra con:
- Header con logo y datos empresa (desde frontend)
- Datos del proveedor
- Tabla de productos con estilos
- Totales
- Código QR de verificación
- Código de barras del número de compra
- Footer legal

IMPORTANTE: Los datos de empresa vienen del FRONTEND.
El backend solo necesita el ID de la compra.
"""

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, mm, cm
from io import BytesIO

from .utils import (
    ColoresERP,
    obtener_estilos,
    construir_header_empresa,
    construir_tabla_productos,
    construir_tabla_totales,
    construir_footer,
    generar_qr,
    generar_codigo_barras,
    formatear_fecha,
    numero_a_letras,
)


def generar_pdf_compra(compra, empresa: dict) -> BytesIO:
    """
    Genera PDF oficial de Orden de Compra.

    Args:
        compra: Instancia del modelo Compra (con .detalles, .proveedor, etc.)
        empresa: dict con datos de empresa enviados desde el frontend:
            {
                "nombre": "FERRESOFT 360 S.A.S",
                "nit": "900123456-7",
                "regimen": "Régimen Común - Responsable de IVA",
                "direccion": "Calle 10 # 5-23",
                "ciudad": "Bogotá D.C.",
                "telefono": "601 234 5678",
                "email": "info@ferresoft.com",
                "logo_base64": "data:image/png;base64,..."   ← desde frontend
            }

    Returns:
        BytesIO: PDF listo para HttpResponse

    Uso en view:
        pdf = generar_pdf_compra(compra, empresa_data)
        return HttpResponse(pdf, content_type='application/pdf')
    """
    buffer = BytesIO()
    c = ColoresERP
    estilos = obtener_estilos()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Orden de Compra {compra.numero_compra}",
        author=empresa.get("nombre", "ERP"),
    )

    elements = []

    # ═══════════════════════════════════════════════════════════════════════
    # 1. HEADER (logo + empresa + título + número)
    # ═══════════════════════════════════════════════════════════════════════

    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="ORDEN DE COMPRA",
        doc_numero=compra.numero_compra,
        doc_fecha=formatear_fecha(str(compra.fecha)),
    )
    elements.append(header)

    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=c.AZUL_PRINCIPAL,
            spaceAfter=12,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 2. BLOQUE DE INFORMACIÓN (Proveedor + Estado)
    # ═══════════════════════════════════════════════════════════════════════

    proveedor = compra.proveedor

    info_data = [
        [
            # Celda proveedor
            [
                Paragraph("PROVEEDOR", estilos["etiqueta"]),
                Paragraph(proveedor.nombre, estilos["valor_bold"]),
                Paragraph(
                    f"NIT/CC: {getattr(proveedor, 'documento', '-')}", estilos["valor"]
                ),
                Paragraph(
                    f"Tel: {getattr(proveedor, 'telefono', '-')}", estilos["valor"]
                ),
                Paragraph(
                    f"Email: {getattr(proveedor, 'email', '-')}", estilos["valor"]
                ),
            ],
            # Celda estado / info
            [
                Paragraph("ESTADO", estilos["etiqueta"]),
                Paragraph(compra.estado, estilos["valor_bold"]),
                Spacer(1, 6),
                Paragraph("USUARIO", estilos["etiqueta"]),
                Paragraph(
                    str(compra.usuario) if hasattr(compra, "usuario") else "-",
                    estilos["valor"],
                ),
            ],
        ]
    ]

    tabla_info = Table(info_data, colWidths=["55%", "45%"])
    tabla_info.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), c.GRIS_FONDO),
                ("BOX", (0, 0), (-1, -1), 0.5, c.BORDE_TABLA),
                ("LINEAFTER", (0, 0), (0, 0), 0.5, c.BORDE_TABLA),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(tabla_info)
    elements.append(Spacer(1, 14))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. TABLA DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════════════════

    elements.append(Paragraph("DETALLE DE PRODUCTOS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    detalles_data = []
    for d in compra.detalles.select_related("producto").all():
        detalles_data.append(
            {
                "codigo": getattr(d.producto, "codigo", "-"),
                "nombre": d.producto.nombre,
                "cantidad": d.cantidad,
                "precio": float(d.precio_compra),
                "subtotal": float(d.subtotal),
            }
        )

    tabla_prod = construir_tabla_productos(detalles_data)
    elements.append(tabla_prod)
    elements.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════════
    # 4. TOTALES + QR + CÓDIGO DE BARRAS (en 2 columnas)
    # ═══════════════════════════════════════════════════════════════════════

    subtotal = float(compra.total)  # Ajusta si tu modelo tiene subtotal separado
    total = float(compra.total)

    tabla_totales = construir_tabla_totales(
        subtotal=subtotal,
        total=total,
    )

    # QR con datos de verificación
    qr_data = (
        f"COMPRA:{compra.numero_compra}|"
        f"PROVEEDOR:{proveedor.nombre}|"
        f"TOTAL:{total}|"
        f"FECHA:{compra.fecha}"
    )
    qr_buffer = generar_qr(qr_data)
    qr_img = Image(qr_buffer, width=1.4 * inch, height=1.4 * inch)

    bloque_bottom = Table(
        [[tabla_totales, qr_img]],
        colWidths=["70%", "30%"],
    )
    bloque_bottom.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("ALIGN", (1, 0), (1, 0), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    elements.append(bloque_bottom)
    elements.append(Spacer(1, 6))

    # Total en letras
    elements.append(
        Paragraph(f"<b>Son:</b> {numero_a_letras(total)}", estilos["valor"])
    )
    elements.append(Spacer(1, 10))

    # Código de barras
    bc_buffer = generar_codigo_barras(compra.numero_compra)
    bc_img = Image(bc_buffer, width=3 * inch, height=0.7 * inch)
    bc_table = Table([[bc_img]], colWidths=["100%"])
    bc_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    elements.append(bc_table)
    elements.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. OBSERVACIONES (si las hay)
    # ═══════════════════════════════════════════════════════════════════════

    obs = getattr(compra, "observaciones", None)
    if obs:
        elements.append(Paragraph("OBSERVACIONES", estilos["etiqueta"]))
        elements.append(Paragraph(obs, estilos["valor"]))
        elements.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════
    # 6. FOOTER
    # ═══════════════════════════════════════════════════════════════════════

    for el in construir_footer(empresa):
        elements.append(el)

    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(elements)
    buffer.seek(0)
    return buffer
