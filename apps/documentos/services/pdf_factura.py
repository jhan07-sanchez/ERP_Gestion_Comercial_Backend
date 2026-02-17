# apps/documentos/services/pdf_factura.py
"""
🧮 GENERADOR PDF - FACTURA DE VENTA (Colombia - DIAN)
=====================================================

Genera factura de venta oficial con todos los campos
requeridos para Colombia:
- Resolución DIAN
- Prefijo y numeración autorizada
- Régimen tributario
- IVA desglosado
- Retenciones (si aplica)
- QR con datos fiscales
- Código de barras
- Texto legal obligatorio
"""

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO

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


def generar_pdf_factura(venta, empresa: dict) -> BytesIO:
    """
    Genera Factura de Venta oficial para Colombia.

    Args:
        venta: Instancia del modelo Venta (con .detalles, .cliente, etc.)
        empresa: dict con datos de empresa desde el frontend:
            {
                "nombre": "FERRESOFT 360 S.A.S",
                "nit": "900123456-7",
                "regimen": "Régimen Común - Responsable de IVA",
                "direccion": "Calle 10 # 5-23",
                "ciudad": "Bogotá D.C.",
                "telefono": "601 234 5678",
                "email": "info@ferresoft.com",
                "logo_base64": "...",
                # Datos DIAN
                "resolucion_dian": "18764030615779",
                "resolucion_fecha": "2023-01-15",
                "resolucion_desde": 1,
                "resolucion_hasta": 1000,
                "resolucion_vigencia": "2025-01-15",
                "prefijo_factura": "FV",
                "texto_legal": "Texto legal de la empresa...",
            }

    Returns:
        BytesIO: PDF listo para HttpResponse
    """
    buffer = BytesIO()
    c = ColoresERP
    estilos = obtener_estilos()

    # Número completo de factura
    prefijo = empresa.get("prefijo_factura", "FV")
    numero_factura = f"{prefijo}{getattr(venta, 'numero_venta', venta.id):05d}"

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

    # ═══════════════════════════════════════════════════════════════════════
    # 1. HEADER EMPRESA + TÍTULO FACTURA
    # ═══════════════════════════════════════════════════════════════════════

    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="FACTURA DE VENTA",
        doc_numero=numero_factura,
        doc_fecha=formatear_fecha(str(venta.fecha)),
    )
    elements.append(header)

    elements.append(
        HRFlowable(
            width="100%",
            thickness=2,
            color=c.AZUL_PRINCIPAL,
            spaceAfter=6,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 2. BLOQUE DIAN (resolución, rango autorizado)
    # ═══════════════════════════════════════════════════════════════════════

    resolucion = empresa.get("resolucion_dian")
    if resolucion:
        dian_text = (
            f"<b>Autorización DIAN:</b> Resolución N° {resolucion} "
            f"del {formatear_fecha(empresa.get('resolucion_fecha', ''))} "
            f"· Rango: {empresa.get('resolucion_desde', '')} al "
            f"{empresa.get('resolucion_hasta', '')} "
            f"· Vigencia: {formatear_fecha(empresa.get('resolucion_vigencia', ''))}"
        )
        dian_style = ParagraphStyle(
            "dian",
            fontSize=7,
            fontName="Helvetica",
            textColor=c.GRIS_MEDIO,
            alignment=TA_CENTER,
        )
        elements.append(Paragraph(dian_text, dian_style))
        elements.append(Spacer(1, 8))

    # ═══════════════════════════════════════════════════════════════════════
    # 3. BLOQUE CLIENTE + CONDICIONES
    # ═══════════════════════════════════════════════════════════════════════

    cliente = venta.cliente

    info_data = [
        [
            # Cliente
            [
                Paragraph("CLIENTE / COMPRADOR", estilos["etiqueta"]),
                Paragraph(
                    getattr(cliente, "nombre", str(cliente)), estilos["valor_bold"]
                ),
                Paragraph(
                    f"NIT/CC: {getattr(cliente, 'documento', '-')}", estilos["valor"]
                ),
                Paragraph(
                    f"Dir: {getattr(cliente, 'direccion', '-')}", estilos["valor"]
                ),
                Paragraph(
                    f"Tel: {getattr(cliente, 'telefono', '-')}", estilos["valor"]
                ),
                Paragraph(f"Email: {getattr(cliente, 'email', '-')}", estilos["valor"]),
            ],
            # Condiciones
            [
                Paragraph("CONDICIONES", estilos["etiqueta"]),
                Paragraph(
                    f"Método de pago: {getattr(venta, 'metodo_pago', 'CONTADO')}",
                    estilos["valor"],
                ),
                Spacer(1, 4),
                Paragraph("VENDEDOR", estilos["etiqueta"]),
                Paragraph(
                    str(venta.usuario) if hasattr(venta, "usuario") else "-",
                    estilos["valor"],
                ),
                Spacer(1, 4),
                Paragraph("OBSERVACIONES", estilos["etiqueta"]),
                Paragraph(
                    getattr(venta, "observaciones", "-") or "-", estilos["valor"]
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
    # 4. TABLA DE PRODUCTOS
    # ═══════════════════════════════════════════════════════════════════════

    elements.append(Paragraph("DETALLE DE PRODUCTOS / SERVICIOS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    detalles_data = []
    subtotal_bruto = 0.0

    for d in venta.detalles.select_related("producto").all():
        precio = float(d.precio_venta)
        cantidad = float(d.cantidad)
        sub = precio * cantidad
        subtotal_bruto += sub

        detalles_data.append(
            {
                "codigo": getattr(d.producto, "codigo", "-"),
                "nombre": d.producto.nombre,
                "cantidad": d.cantidad,
                "precio": precio,
                "subtotal": sub,
            }
        )

    elements.append(construir_tabla_productos(detalles_data))
    elements.append(Spacer(1, 12))

    # ═══════════════════════════════════════════════════════════════════════
    # 5. BLOQUE TOTALES + QR
    # ═══════════════════════════════════════════════════════════════════════

    total_final = float(venta.total)
    iva_pct = getattr(venta, "iva_porcentaje", 0) or 0
    descuento = getattr(venta, "descuento", 0) or 0
    iva_valor = subtotal_bruto * (iva_pct / 100)

    # Tabla de totales detallada
    filas_totales = []
    filas_totales.append(
        [
            Paragraph("Subtotal:", estilos["etiqueta"]),
            Paragraph(f"${subtotal_bruto:,.2f}", estilos["valor"]),
        ]
    )
    if descuento > 0:
        filas_totales.append(
            [
                Paragraph("Descuento:", estilos["etiqueta"]),
                Paragraph(
                    f"-${float(descuento):,.2f}",
                    ParagraphStyle(
                        "dc", fontSize=9, textColor=c.ROJO_ERROR, alignment=TA_RIGHT
                    ),
                ),
            ]
        )
    if iva_pct > 0:
        filas_totales.append(
            [
                Paragraph(f"IVA ({iva_pct:.0f}%):", estilos["etiqueta"]),
                Paragraph(f"${iva_valor:,.2f}", estilos["valor"]),
            ]
        )
    filas_totales.append(
        [
            Paragraph("TOTAL A PAGAR:", estilos["total_label"]),
            Paragraph(f"${total_final:,.2f}", estilos["total_valor"]),
        ]
    )

    t_totales = Table(filas_totales, colWidths=["60%", "40%"])
    t_totales.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, c.AZUL_PRINCIPAL),
                ("TOPPADDING", (0, -1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    # QR fiscal
    qr_data = (
        f"FACTURA:{numero_factura}|"
        f"NIT:{empresa.get('nit', '')}|"
        f"CLIENTE:{getattr(cliente, 'documento', '')}|"
        f"TOTAL:{total_final}|"
        f"IVA:{iva_valor:.2f}|"
        f"FECHA:{venta.fecha}"
    )
    qr_buffer = generar_qr(qr_data)
    qr_img = Image(qr_buffer, width=1.4 * inch, height=1.4 * inch)

    bloque_bottom = Table(
        [[t_totales, qr_img]],
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
        Paragraph(f"<b>Son:</b> {numero_a_letras(total_final)}", estilos["valor"])
    )
    elements.append(Spacer(1, 10))

    # Código de barras
    bc_buffer = generar_codigo_barras(numero_factura)
    bc_img = Image(bc_buffer, width=3 * inch, height=0.7 * inch)
    bc_table = Table([[bc_img]], colWidths=["100%"])
    bc_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(bc_table)
    elements.append(Spacer(1, 10))

    # ═══════════════════════════════════════════════════════════════════════
    # 6. TEXTO LEGAL
    # ═══════════════════════════════════════════════════════════════════════

    texto_legal_empresa = empresa.get("texto_legal", "")
    texto_legal_base = (
        "Este documento es equivalente a una factura de venta según el "
        "Decreto 1165 del 2 de julio de 2019 y el Artículo 616-1 del "
        "Estatuto Tributario. Conserve este documento para efectos fiscales."
    )

    for el in construir_footer(
        empresa, texto_extra=texto_legal_empresa or texto_legal_base
    ):
        elements.append(el)

    doc.build(elements)
    buffer.seek(0)
    return buffer
