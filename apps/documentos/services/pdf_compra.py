# apps/documentos/services/pdf_compra.py
"""
📦 GENERADOR PDF - ORDEN DE COMPRA — Versión Empresarial
======================================================

Genera PDF oficial de compra con layout profesional.
Mejoras v2:
- Integración con UUID y Hash de verificación.
- Fechas legibles (formato largo).
- QR profesional con JSON serializado.
- Diseño consistente con el resto de comprobantes.
"""

import json
from io import BytesIO

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
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER

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


def generar_pdf_compra(documento, empresa: dict) -> BytesIO:
    """
    Genera PDF oficial de Orden de Compra desde el modelo Documento.
    """
    buffer = BytesIO()
    c = ColoresERP
    estilos = obtener_estilos()

    # 1. Obtener datos de origen
    compra = documento.compra
    if not compra:
        raise ValueError("El documento no está asociado a una compra.")

    numero_compra = documento.numero_interno
    fecha_doc = documento.fecha_emision

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Orden de Compra {numero_compra}",
        author=empresa.get("nombre", "ERP"),
    )

    elements = []

    # ── 1. HEADER ─────────────────────────────────────────────────────────
    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="ORDEN DE COMPRA",
        doc_numero=numero_compra,
        doc_fecha=formatear_fecha(fecha_doc, formato="largo"),
    )
    elements.append(header)

    elements.append(HRFlowable(width="100%", thickness=2, color=c.AZUL_PRINCIPAL, spaceAfter=12))

    # ── 2. BLOQUE DE INFORMACIÓN (Proveedor + Estado) ─────────────────────
    proveedor = compra.proveedor
    nombre_prov = getattr(proveedor, "nombre", str(proveedor))

    info_data = [
        [
            # Columna Proveedor
            [
                Paragraph("PROVEEDOR / EMISOR", estilos["etiqueta"]),
                Paragraph(nombre_prov, estilos["valor_bold"]),
                Paragraph(f"NIT/CC: {getattr(proveedor, 'documento', '-')}", estilos["valor"]),
                Paragraph(f"Teléfono: {getattr(proveedor, 'telefono', '-')}", estilos["valor"]),
                Paragraph(f"Email: {getattr(proveedor, 'email', '-')}", estilos["valor"]),
            ],
            # Columna Info Compra
            [
                Paragraph("ESTADO DE LA OPERACIÓN", estilos["etiqueta"]),
                Paragraph(compra.estado.upper(), estilos["valor_bold"]),
                Spacer(1, 6),
                Paragraph("USUARIO QUE REGISTRA", estilos["etiqueta"]),
                Paragraph(str(documento.usuario) if documento.usuario else "-", estilos["valor"]),
            ],
        ]
    ]

    tabla_info = Table(info_data, colWidths=["55%", "45%"])
    tabla_info.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), c.GRIS_FONDO),
        ("BOX", (0, 0), (-1, -1), 0.5, c.BORDE_TABLA),
        ("LINEAFTER", (0, 0), (0, 0), 0.5, c.BORDE_TABLA),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    elements.append(tabla_info)
    elements.append(Spacer(1, 14))

    # ── 3. DETALLES DE PRODUCTOS (Desde DocumentoDetalle) ──────────────────
    elements.append(Paragraph("DETALLE DE PRODUCTOS ADQUIRIDOS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    detalles_data = []
    for d in documento.lineas.all().order_by("orden"):
        detalles_data.append({
            "codigo": str(d.producto_id) if d.producto_id else "-",
            "nombre": d.descripcion,
            "cantidad": float(d.cantidad),
            "precio": float(d.precio_unitario),
            "subtotal": float(d.subtotal),
        })

    tabla_prod = construir_tabla_productos(detalles_data)
    elements.append(tabla_prod)
    elements.append(Spacer(1, 12))

    # ── 4. TOTALES + QR ───────────────────────────────────────────────────
    total = float(documento.total)
    
    # Tabla Totales (simplificada para compras si no hay desglose IVA en el modelo)
    tabla_totales = construir_tabla_totales(
        subtotal=float(documento.subtotal),
        total=total,
    )

    # QR Profesional
    hash_v = documento.codigo_verificacion or "-"

    qr_payload = {
        "com": numero_compra,
        "nit": empresa.get("nit", ""),
        "prv": nombre_prov,
        "tot": total,
        "fec": str(fecha_doc)[:10],
        "hash": hash_v
    }
    qr_data = json.dumps(qr_payload)
    qr_buffer = generar_qr(qr_data)
    qr_img = Image(qr_buffer, width=1.4 * inch, height=1.4 * inch)

    bloque_bottom = Table([[tabla_totales, qr_img]], colWidths=["70%", "30%"])
    bloque_bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(bloque_bottom)
    elements.append(Spacer(1, 6))

    # ── 5. FINALIZACIÓN ──────────────────────────────────────────────────
    # Total en letras
    elements.append(Paragraph(f"<b>Son:</b> {numero_a_letras(total)}", estilos["valor"]))
    elements.append(Spacer(1, 10))

    # Código de barras
    bc_buffer = generar_codigo_barras(numero_compra)
    bc_img = Image(bc_buffer, width=3 * inch, height=0.7 * inch)
    bc_table = Table([[bc_img]], colWidths=["100%"])
    bc_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(bc_table)
    
    if hash_v != "-":
        verify_style = ParagraphStyle("vd", parent=estilos["footer"], fontSize=7)
        elements.append(Paragraph(f"Código de verificación: <b>{hash_v}</b>", verify_style))

    elements.append(Spacer(1, 10))

    # Observaciones
    obs = documento.notas or getattr(compra, "observaciones", None)
    if obs:
        elements.append(Paragraph("OBSERVACIONES / NOTAS ADICIONALES", estilos["etiqueta"]))
        elements.append(Paragraph(obs, estilos["valor"]))
        elements.append(Spacer(1, 10))

    # Footer
    for el in construir_footer(empresa):
        elements.append(el)

    # Build
    doc.build(elements)
    buffer.seek(0)
    return buffer

