# apps/documentos/services/pdf_factura.py
"""
🧮 GENERADOR PDF - FACTURA DE VENTA (Colombia - DIAN) — Versión Empresarial
========================================================================

Genera factura de venta oficial con todos los campos requeridos para Colombia.
Optimizado para auditoría y cumplimiento fiscal.

Mejoras v2:
- Integración con UUID y Hash de verificación.
- Fechas legibles (formato largo).
- QR profesional con JSON serializado.
- Bloques informativos mejor organizados.
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
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from .utils import (
    ColoresERP,
    obtener_estilos,
    construir_header_empresa,
    construir_tabla_productos,
    construir_footer,
    generar_qr,
    generar_codigo_barras,
    formatear_fecha,
    numero_a_letras,
)


def generar_pdf_factura(documento, empresa: dict) -> BytesIO:
    """
    Genera Factura de Venta oficial para Colombia desde un modelo Documento.
    """
    buffer = BytesIO()
    c = ColoresERP
    estilos = obtener_estilos()

    # 1. Obtener datos de origen
    venta = documento.venta
    if not venta:
        raise ValueError("El documento no está asociado a una venta.")

    numero_factura = documento.numero_interno
    fecha_doc = documento.fecha_emision

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
        title=f"Factura {numero_factura}",
        author=empresa.get("nombre", "ERP"),
    )

    elements = []

    # ── 1. HEADER EMPRESA + TÍTULO FACTURA ────────────────────────────────
    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="FACTURA DE VENTA",
        doc_numero=numero_factura,
        doc_fecha=formatear_fecha(fecha_doc, formato="largo"),
    )
    elements.append(header)

    elements.append(HRFlowable(width="100%", thickness=2, color=c.AZUL_PRINCIPAL, spaceAfter=6))

    # ── 2. BLOQUE DIAN (Resolución) ──────────────────────────────────────
    resolucion = empresa.get("resolucion_dian")
    if resolucion:
        dian_text = (
            f"<b>Autorización DIAN:</b> Resolución N° {resolucion} "
            f"del {formatear_fecha(empresa.get('resolucion_fecha', ''), 'largo')} "
            f"· Rango: {empresa.get('resolucion_desde', '')} al "
            f"{empresa.get('resolucion_hasta', '')} "
            f"· Vigencia: {formatear_fecha(empresa.get('resolucion_vigencia', ''), 'largo')}"
        )
        dian_style = ParagraphStyle("dian", parent=estilos["empresa_dato"], alignment=TA_CENTER, textColor=c.GRIS_MEDIO)
        elements.append(Paragraph(dian_text, dian_style))
        elements.append(Spacer(1, 8))

    # ── 3. BLOQUE CLIENTE + CONDICIONES ───────────────────────────────────
    cliente = venta.cliente
    nombre_cliente = getattr(cliente, "nombre", str(cliente))
    
    info_data = [
        [
            # Columna Cliente
            [
                Paragraph("CLIENTE / COMPRADOR", estilos["etiqueta"]),
                Paragraph(nombre_cliente, estilos["valor_bold"]),
                Paragraph(f"NIT/CC: {getattr(cliente, 'documento', '-')}", estilos["valor"]),
                Paragraph(f"Dirección: {getattr(cliente, 'direccion', '-')}", estilos["valor"]),
                Paragraph(f"Teléfono: {getattr(cliente, 'telefono', '-')}", estilos["valor"]),
                Paragraph(f"Email: {getattr(cliente, 'email', '-')}", estilos["valor"]),
            ],
            # Columna Condiciones
            [
                Paragraph("CONDICIONES DE VENTA", estilos["etiqueta"]),
                Paragraph(f"Método de pago: {getattr(venta, 'metodo_pago', 'CONTADO')}", estilos["valor"]),
                Spacer(1, 4),
                Paragraph("VENDEDOR", estilos["etiqueta"]),
                Paragraph(str(documento.usuario) if documento.usuario else "-", estilos["valor"]),
                Spacer(1, 4),
                Paragraph("OBSERVACIONES", estilos["etiqueta"]),
                Paragraph(documento.notas or getattr(venta, "observaciones", "-") or "-", estilos["valor"]),
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

    # ── 4. TABLA DE PRODUCTOS (Desde DocumentoDetalle - Snapshot) ─────────
    elements.append(Paragraph("DETALLE DE PRODUCTOS / SERVICIOS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    detalles_data = []
    # Usamos las líneas persistentes del documento
    for d in documento.lineas.all().order_by("orden"):
        detalles_data.append({
            "codigo": str(d.producto_id) if d.producto_id else "-",
            "nombre": d.descripcion,
            "cantidad": float(d.cantidad),
            "precio": float(d.precio_unitario),
            "subtotal": float(d.subtotal),
        })

    elements.append(construir_tabla_productos(detalles_data))
    elements.append(Spacer(1, 12))

    # ── 5. TOTALES + QR ───────────────────────────────────────────────────
    total_final = float(documento.total)
    subtotal_acumulado = float(documento.subtotal)
    # En el futuro, Documento debería guardar el % de IVA explícito. 
    # Por ahora lo calculamos o lo traemos de la venta para el desglose visual.
    iva_pct = float(getattr(venta, "iva_porcentaje", 0) or 0)
    descuento = float(getattr(venta, "descuento", 0) or 0)
    iva_valor = float(documento.impuestos) if documento.impuestos > 0 else (subtotal_acumulado * (iva_pct / 100) if iva_pct > 0 else 0)

    filas_totales = [
        [Paragraph("Subtotal:", estilos["etiqueta"]), Paragraph(f"${subtotal_acumulado:,.2f}", estilos["valor"])]
    ]
    if descuento > 0:
        filas_totales.append([
            Paragraph("Descuento:", estilos["etiqueta"]), 
            Paragraph(f"-${descuento:,.2f}", ParagraphStyle("dc", parent=estilos["valor"], textColor=c.ROJO_ERROR, alignment=TA_RIGHT))
        ])
    if iva_valor > 0:
        label_iva = f"IVA ({iva_pct:.0f}%):" if iva_pct > 0 else "Impuestos:"
        filas_totales.append([
            Paragraph(label_iva, estilos["etiqueta"]),
            Paragraph(f"${iva_valor:,.2f}", estilos["valor"])
        ])
    
    filas_totales.append([
        Paragraph("TOTAL A PAGAR:", estilos["total_label"]),
        Paragraph(f"${total_final:,.2f}", estilos["total_valor"])
    ])

    t_totales = Table(filas_totales, colWidths=["60%", "40%"])
    t_totales.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("LINEABOVE", (0, -1), (-1, -1), 1.5, c.AZUL_PRINCIPAL),
        ("TOPPADDING", (0, -1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    # QR Profesional (JSON)
    hash_v = documento.codigo_verificacion or "-"

    qr_payload = {
        "doc": numero_factura,
        "nit": empresa.get("nit", ""),
        "cli": getattr(cliente, 'documento', ''),
        "tot": total_final,
        "iva": round(iva_valor, 2),
        "fec": str(fecha_doc)[:10],
        "hash": hash_v
    }
    qr_data = json.dumps(qr_payload)
    qr_buffer = generar_qr(qr_data)
    qr_img = Image(qr_buffer, width=1.5 * inch, height=1.5 * inch)

    bloque_bottom = Table([[t_totales, qr_img]], colWidths=["65%", "35%"])
    bloque_bottom.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))

    elements.append(bloque_bottom)
    elements.append(Spacer(1, 6))

    # ── 6. FINALIZACIÓN ──────────────────────────────────────────────────
    # Total en letras
    elements.append(Paragraph(f"<b>Son:</b> {numero_a_letras(total_final)}", estilos["valor"]))
    elements.append(Spacer(1, 10))

    # Código de barras
    bc_buffer = generar_codigo_barras(numero_factura)
    bc_img = Image(bc_buffer, width=3 * inch, height=0.7 * inch)
    bc_table = Table([[bc_img]], colWidths=["100%"])
    bc_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(bc_table)
    
    if hash_v != "-":
        verify_style = ParagraphStyle("vd", parent=estilos["footer"], fontSize=7)
        elements.append(Paragraph(f"Código de verificación: <b>{hash_v}</b>", verify_style))

    elements.append(Spacer(1, 15))

    # Footer legal
    texto_legal = empresa.get("texto_legal", "") or (
        "Este documento es equivalente a una factura de venta según el Decreto 1165 del 2 de julio de 2019 "
        "y el Artículo 616-1 del Estatuto Tributario. Conserve este documento para efectos fiscales."
    )

    for el in construir_footer(empresa, texto_extra=texto_legal):
        elements.append(el)

    # Construir PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

