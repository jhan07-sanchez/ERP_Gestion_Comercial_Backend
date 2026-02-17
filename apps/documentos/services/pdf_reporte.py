# apps/documentos/services/pdf_reporte.py
"""
📊 GENERADOR PDF - REPORTES GERENCIALES
=========================================

Genera reportes en PDF con:
- Reporte de Ventas por período
- Reporte de Compras por período
- Reporte de Utilidad / Rentabilidad
- Reporte de Inventario

Todos incluyen:
- Gráficas de barra simples (con ReportLab Drawing)
- Tablas con totales
- Resumen ejecutivo
- QR de verificación del reporte
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
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from io import BytesIO
from datetime import datetime

from .utils import (
    ColoresERP,
    obtener_estilos,
    construir_header_empresa,
    construir_footer,
    generar_qr,
    formatear_fecha,
)


# ============================================================================
# REPORTE DE VENTAS
# ============================================================================


def generar_reporte_ventas(
    ventas_qs, empresa: dict, fecha_inicio: str, fecha_fin: str
) -> BytesIO:
    """
    Genera reporte de ventas por período.

    Args:
        ventas_qs: QuerySet de ventas en el período
        empresa: dict con datos de empresa desde el frontend
        fecha_inicio: "YYYY-MM-DD"
        fecha_fin: "YYYY-MM-DD"

    Returns:
        BytesIO: PDF del reporte
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
        title=f"Reporte de Ventas {fecha_inicio} al {fecha_fin}",
    )

    elements = []

    # ── Header ───────────────────────────────────────────────────────────
    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="REPORTE DE VENTAS",
        doc_numero=f"RV-{datetime.now().strftime('%Y%m%d%H%M')}",
        doc_fecha=f"{formatear_fecha(fecha_inicio)} al {formatear_fecha(fecha_fin)}",
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

    # ── Calcular métricas ─────────────────────────────────────────────────
    ventas = list(ventas_qs.select_related("cliente", "usuario"))
    total_ventas = sum(float(v.total) for v in ventas)
    total_docs = len(ventas)
    ticket_promedio = total_ventas / total_docs if total_docs > 0 else 0

    ventas_realizadas = [v for v in ventas if v.estado == "REALIZADA"]
    ventas_anuladas = [v for v in ventas if v.estado == "ANULADA"]

    # ── Tarjetas de resumen ───────────────────────────────────────────────
    resumen_data = [
        [
            [
                Paragraph("TOTAL VENTAS", estilos["etiqueta"]),
                Paragraph(f"${total_ventas:,.2f}", estilos["total_valor"]),
            ],
            [
                Paragraph("N° DOCUMENTOS", estilos["etiqueta"]),
                Paragraph(str(total_docs), estilos["total_valor"]),
            ],
            [
                Paragraph("TICKET PROMEDIO", estilos["etiqueta"]),
                Paragraph(f"${ticket_promedio:,.2f}", estilos["total_valor"]),
            ],
            [
                Paragraph("ANULADAS", estilos["etiqueta"]),
                Paragraph(str(len(ventas_anuladas)), estilos["valor_bold"]),
            ],
        ]
    ]

    t_resumen = Table(resumen_data, colWidths=["25%", "25%", "25%", "25%"])
    t_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c.AZUL_FONDO),
                ("BOX", (0, 0), (-1, -1), 1, c.AZUL_CLARO),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c.BORDE_TABLA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    elements.append(t_resumen)
    elements.append(Spacer(1, 14))

    # ── Tabla detallada de ventas ─────────────────────────────────────────
    elements.append(Paragraph("DETALLE DE VENTAS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    data_tabla = [["N° Venta", "Fecha", "Cliente", "Estado", "Total"]]

    for v in ventas_realizadas[:50]:  # Máximo 50 filas
        data_tabla.append(
            [
                getattr(v, "numero_venta", f"VT-{v.id:05d}"),
                str(v.fecha)[:10],
                getattr(v.cliente, "nombre", str(v.cliente))[:25],
                v.estado,
                f"${float(v.total):,.2f}",
            ]
        )

    # Fila de total
    data_tabla.append(["", "", "", "TOTAL:", f"${total_ventas:,.2f}"])

    tabla_ventas = Table(
        data_tabla,
        colWidths=["18%", "15%", "37%", "14%", "16%"],
    )
    tabla_ventas.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), c.HEADER_TABLA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                # Cuerpo
                ("FONTNAME", (0, 1), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -2), 7),
                ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                # Alternado
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [c.FILA_IMPAR, c.FILA_PAR]),
                # Fila de total
                ("BACKGROUND", (0, -1), (-1, -1), c.AZUL_FONDO),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 8),
                ("LINEABOVE", (0, -1), (-1, -1), 1, c.AZUL_PRINCIPAL),
                # Bordes
                ("GRID", (0, 0), (-1, -1), 0.3, c.BORDE_TABLA),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(tabla_ventas)
    elements.append(Spacer(1, 10))

    # QR del reporte
    qr_data = (
        f"REPORTE_VENTAS|"
        f"EMPRESA:{empresa.get('nit', '')}|"
        f"DESDE:{fecha_inicio}|"
        f"HASTA:{fecha_fin}|"
        f"TOTAL:{total_ventas:.2f}"
    )
    qr_buffer = generar_qr(qr_data)
    qr_img = Image(qr_buffer, width=1 * inch, height=1 * inch)
    qr_table = Table([[qr_img]], colWidths=["100%"])
    qr_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "RIGHT")]))
    elements.append(qr_table)

    for el in construir_footer(
        empresa, "Reporte generado por el sistema ERP. Uso interno."
    ):
        elements.append(el)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ============================================================================
# REPORTE DE COMPRAS
# ============================================================================


def generar_reporte_compras(
    compras_qs, empresa: dict, fecha_inicio: str, fecha_fin: str
) -> BytesIO:
    """
    Genera reporte de compras por período.
    Misma estructura que ventas pero para compras.
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
        title=f"Reporte de Compras {fecha_inicio} al {fecha_fin}",
    )

    elements = []

    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="REPORTE DE COMPRAS",
        doc_numero=f"RC-{datetime.now().strftime('%Y%m%d%H%M')}",
        doc_fecha=f"{formatear_fecha(fecha_inicio)} al {formatear_fecha(fecha_fin)}",
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

    compras = list(compras_qs.select_related("proveedor", "usuario"))
    total_compras = sum(float(co.total) for co in compras)
    total_docs = len(compras)

    # Resumen
    resumen_data = [
        [
            [
                Paragraph("TOTAL INVERTIDO", estilos["etiqueta"]),
                Paragraph(f"${total_compras:,.2f}", estilos["total_valor"]),
            ],
            [
                Paragraph("N° ÓRDENES", estilos["etiqueta"]),
                Paragraph(str(total_docs), estilos["total_valor"]),
            ],
            [
                Paragraph("PROMEDIO/ORDEN", estilos["etiqueta"]),
                Paragraph(
                    f"${(total_compras / total_docs if total_docs else 0):,.2f}",
                    estilos["valor_bold"],
                ),
            ],
        ]
    ]

    t_resumen = Table(resumen_data, colWidths=["34%", "33%", "33%"])
    t_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c.AZUL_FONDO),
                ("BOX", (0, 0), (-1, -1), 1, c.AZUL_CLARO),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c.BORDE_TABLA),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_resumen)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("DETALLE DE COMPRAS", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    data_tabla = [["N° Compra", "Fecha", "Proveedor", "Estado", "Total"]]

    for co in compras[:50]:
        data_tabla.append(
            [
                co.numero_compra,
                str(co.fecha)[:10],
                co.proveedor.nombre[:25],
                co.estado,
                f"${float(co.total):,.2f}",
            ]
        )

    data_tabla.append(["", "", "", "TOTAL:", f"${total_compras:,.2f}"])

    tabla = Table(data_tabla, colWidths=["18%", "15%", "37%", "14%", "16%"])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), c.HEADER_TABLA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [c.FILA_IMPAR, c.FILA_PAR]),
                ("BACKGROUND", (0, -1), (-1, -1), c.AZUL_FONDO),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, c.AZUL_PRINCIPAL),
                ("GRID", (0, 0), (-1, -1), 0.3, c.BORDE_TABLA),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    elements.append(tabla)
    elements.append(Spacer(1, 10))

    for el in construir_footer(
        empresa, "Reporte generado por el sistema ERP. Uso interno."
    ):
        elements.append(el)

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ============================================================================
# REPORTE DE INVENTARIO
# ============================================================================


def generar_reporte_inventario(productos_qs, empresa: dict) -> BytesIO:
    """
    Genera reporte de inventario actual.

    Args:
        productos_qs: QuerySet de productos con stock
        empresa: dict con datos de empresa desde el frontend
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
        title="Reporte de Inventario",
    )

    elements = []

    header = construir_header_empresa(
        empresa=empresa,
        doc_titulo="REPORTE DE INVENTARIO",
        doc_numero=f"RI-{datetime.now().strftime('%Y%m%d')}",
        doc_fecha=formatear_fecha(datetime.now().strftime("%Y-%m-%d")),
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

    productos = list(productos_qs)
    total_productos = len(productos)
    valor_inventario = sum(
        float(getattr(p, "precio_compra", 0)) * float(getattr(p, "stock_actual", 0))
        for p in productos
    )
    productos_sin_stock = sum(
        1 for p in productos if float(getattr(p, "stock_actual", 0)) <= 0
    )

    # Resumen
    resumen_data = [
        [
            [
                Paragraph("TOTAL PRODUCTOS", estilos["etiqueta"]),
                Paragraph(str(total_productos), estilos["total_valor"]),
            ],
            [
                Paragraph("VALOR INVENTARIO", estilos["etiqueta"]),
                Paragraph(f"${valor_inventario:,.2f}", estilos["total_valor"]),
            ],
            [
                Paragraph("SIN STOCK", estilos["etiqueta"]),
                Paragraph(
                    str(productos_sin_stock),
                    ParagraphStyle(
                        "rs",
                        fontSize=13,
                        fontName="Helvetica-Bold",
                        textColor=c.ROJO_ERROR,
                        alignment=TA_CENTER,
                    ),
                ),
            ],
        ]
    ]

    t_resumen = Table(resumen_data, colWidths=["34%", "33%", "33%"])
    t_resumen.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), c.AZUL_FONDO),
                ("BOX", (0, 0), (-1, -1), 1, c.AZUL_CLARO),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, c.BORDE_TABLA),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_resumen)
    elements.append(Spacer(1, 14))

    elements.append(Paragraph("INVENTARIO ACTUAL", estilos["etiqueta"]))
    elements.append(Spacer(1, 4))

    data_inv = [
        ["Código", "Producto", "Categoría", "Stock", "P. Compra", "P. Venta", "Valor"]
    ]

    for p in productos:
        stock = float(getattr(p, "stock_actual", 0))
        precio_c = float(getattr(p, "precio_compra", 0))
        precio_v = float(getattr(p, "precio_venta", 0))
        valor = stock * precio_c

        data_inv.append(
            [
                getattr(p, "codigo", "-"),
                p.nombre[:28],
                getattr(getattr(p, "categoria", None), "nombre", "-"),
                f"{stock:,.0f}",
                f"${precio_c:,.2f}",
                f"${precio_v:,.2f}",
                f"${valor:,.2f}",
            ]
        )

    data_inv.append(["", "", "", "", "", "TOTAL:", f"${valor_inventario:,.2f}"])

    tabla_inv = Table(
        data_inv,
        colWidths=["10%", "28%", "15%", "9%", "12%", "12%", "14%"],
    )
    tabla_inv.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), c.HEADER_TABLA),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -2), [c.FILA_IMPAR, c.FILA_PAR]),
                ("BACKGROUND", (0, -1), (-1, -1), c.AZUL_FONDO),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 1, c.AZUL_PRINCIPAL),
                ("GRID", (0, 0), (-1, -1), 0.3, c.BORDE_TABLA),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )

    elements.append(tabla_inv)
    elements.append(Spacer(1, 10))

    for el in construir_footer(
        empresa, "Reporte de inventario generado por el sistema ERP."
    ):
        elements.append(el)

    doc.build(elements)
    buffer.seek(0)
    return buffer
