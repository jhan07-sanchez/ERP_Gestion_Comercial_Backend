# apps/documentos/services/recibo_pos.py
"""
🧾 GENERADOR - RECIBO POS TÉRMICO (80mm)
==========================================

Genera recibo para impresora térmica de 80mm.

CARACTERÍSTICAS:
- Página de 80mm de ancho (altura dinámica)
- Fuente óptima para impresión térmica
- QR pequeño al final
- Sin imágenes pesadas (excepto logo si existe)
- Totales bien visibles
- Método de pago destacado

IMPORTANTE: Ancho estándar térmica 80mm = ~227 puntos ReportLab
La altura es dinámica según cantidad de productos.
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
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from io import BytesIO

from .utils import (
    obtener_estilos,
    generar_qr,
    generar_codigo_barras,
    formatear_fecha,
    numero_a_letras,
    procesar_logo,
)


# Ancho estándar rollo 80mm (área imprimible ~72mm)
ANCHO_POS = 72 * mm


def _calcular_altura(num_productos: int) -> float:
    """Calcula altura dinámica del ticket según productos."""
    base = 120 * mm
    por_producto = 8 * mm
    return base + (num_productos * por_producto)


def generar_recibo_pos(venta, empresa: dict) -> BytesIO:
    """
    Genera recibo POS de 80mm para impresora térmica.

    Args:
        venta: Instancia del modelo Venta
        empresa: dict con datos de empresa desde el frontend:
            {
                "nombre": "FERRESOFT 360 S.A.S",
                "nit": "900123456-7",
                "direccion": "Calle 10 # 5-23",
                "ciudad": "Bogotá D.C.",
                "telefono": "601 234 5678",
                "email": "info@ferresoft.com",
                "logo_base64": "...",
                "mensaje_pie": "¡Gracias por su compra!",
            }

    Returns:
        BytesIO: PDF optimizado para impresora térmica 80mm
    """
    buffer = BytesIO()
    estilos = obtener_estilos()

    detalles = list(venta.detalles.select_related("producto").all())
    altura = _calcular_altura(len(detalles))

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(ANCHO_POS, altura),
        rightMargin=3 * mm,
        leftMargin=3 * mm,
        topMargin=4 * mm,
        bottomMargin=4 * mm,
        title=f"Recibo {getattr(venta, 'numero_venta', venta.id)}",
    )

    elements = []

    # ═══════════════════════════════════════════════════════════════════════
    # 1. LOGO (opcional, pequeño)
    # ═══════════════════════════════════════════════════════════════════════

    logo_buffer = procesar_logo(empresa.get("logo_base64", ""))
    if logo_buffer:
        logo_img = Image(logo_buffer, width=20 * mm, height=10 * mm)
        logo_table = Table([[logo_img]], colWidths=[ANCHO_POS - 6 * mm])
        logo_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elements.append(logo_table)

    # ═══════════════════════════════════════════════════════════════════════
    # 2. HEADER EMPRESA
    # ═══════════════════════════════════════════════════════════════════════

    elements.append(Paragraph(empresa.get("nombre", "EMPRESA"), estilos["pos_empresa"]))

    if empresa.get("nit"):
        elements.append(Paragraph(f"NIT: {empresa['nit']}", estilos["pos_dato"]))

    if empresa.get("direccion"):
        elements.append(Paragraph(empresa["direccion"], estilos["pos_dato"]))

    if empresa.get("ciudad"):
        elements.append(Paragraph(empresa["ciudad"], estilos["pos_dato"]))

    if empresa.get("telefono"):
        elements.append(Paragraph(f"Tel: {empresa['telefono']}", estilos["pos_dato"]))

    elements.append(Spacer(1, 2 * mm))
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=1,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 3. DATOS DEL RECIBO
    # ═══════════════════════════════════════════════════════════════════════

    numero = getattr(venta, "numero_venta", f"VT-{venta.id:05d}")

    elements.append(Paragraph("RECIBO DE VENTA", estilos["pos_titulo"]))
    elements.append(Paragraph(f"N° {numero}", estilos["pos_empresa"]))
    elements.append(Paragraph(formatear_fecha(str(venta.fecha)), estilos["pos_dato"]))

    elements.append(Spacer(1, 2 * mm))
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=0.5,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )

    # Cliente
    cliente = venta.cliente
    elements.append(
        Paragraph(
            f"Cliente: {getattr(cliente, 'nombre', str(cliente))}", estilos["pos_bold"]
        )
    )
    if getattr(cliente, "documento", None):
        elements.append(
            Paragraph(f"CC/NIT: {cliente.documento}", estilos["pos_normal"])
        )

    elements.append(Spacer(1, 2 * mm))
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=0.5,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 4. TABLA DE PRODUCTOS (formato compacto)
    # ═══════════════════════════════════════════════════════════════════════

    # Header de productos
    elements.append(Paragraph("DESCRIPCIÓN        CANT  TOTAL", estilos["pos_bold"]))
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=0.3,
            color=colors.black,
            spaceAfter=1 * mm,
        )
    )

    total_general = 0.0

    for d in detalles:
        precio = float(d.precio_venta)
        cantidad = float(d.cantidad)
        sub = precio * cantidad
        total_general += sub

        nombre = d.producto.nombre[:22]  # Truncar para 80mm

        # Línea nombre + precio unitario
        elements.append(Paragraph(nombre, estilos["pos_bold"]))

        # Línea cantidad x precio = subtotal
        linea_calculo = Table(
            [
                [
                    Paragraph(
                        f"  {cantidad:.0f} x ${precio:,.0f}", estilos["pos_normal"]
                    ),
                    Paragraph(
                        f"${sub:,.0f}",
                        ParagraphStyle(
                            "pos_right",
                            fontSize=8,
                            fontName="Helvetica",
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            ],
            colWidths=["65%", "35%"],
        )
        linea_calculo.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        elements.append(linea_calculo)

    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=1,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 5. TOTALES
    # ═══════════════════════════════════════════════════════════════════════

    total_final = float(venta.total)
    iva_pct = getattr(venta, "iva_porcentaje", 0) or 0
    descuento = getattr(venta, "descuento", 0) or 0

    def linea_total(label, valor, bold=False):
        estilo = "pos_bold" if bold else "pos_normal"
        t = Table(
            [
                [
                    Paragraph(label, estilos[estilo]),
                    Paragraph(
                        f"${float(valor):,.0f}",
                        ParagraphStyle(
                            "pr",
                            fontSize=8 if not bold else 11,
                            fontName="Helvetica-Bold" if bold else "Helvetica",
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            ],
            colWidths=["55%", "45%"],
        )
        t.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        return t

    elements.append(linea_total("Subtotal:", total_general))

    if descuento > 0:
        elements.append(linea_total("Descuento:", -float(descuento)))

    if iva_pct > 0:
        iva_valor = total_general * (iva_pct / 100)
        elements.append(linea_total(f"IVA ({iva_pct:.0f}%):", iva_valor))

    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=1.5,
            color=colors.black,
            spaceAfter=1 * mm,
        )
    )

    elements.append(linea_total("TOTAL:", total_final, bold=True))

    elements.append(Spacer(1, 2 * mm))

    # Método de pago
    metodo = getattr(venta, "metodo_pago", "EFECTIVO")
    elements.append(Paragraph(f"Forma de pago: {metodo}", estilos["pos_bold"]))

    # Si es efectivo, mostrar cambio
    efectivo_recibido = getattr(venta, "efectivo_recibido", None)
    if efectivo_recibido and float(efectivo_recibido) > 0:
        cambio = float(efectivo_recibido) - total_final
        elements.append(linea_total("Efectivo:", float(efectivo_recibido)))
        if cambio >= 0:
            elements.append(linea_total("Cambio:", cambio, bold=True))

    elements.append(Spacer(1, 3 * mm))
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=0.5,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )

    # ═══════════════════════════════════════════════════════════════════════
    # 6. QR DE VERIFICACIÓN
    # ═══════════════════════════════════════════════════════════════════════

    qr_data = (
        f"RECIBO:{numero}|"
        f"NIT:{empresa.get('nit', '')}|"
        f"TOTAL:{total_final}|"
        f"FECHA:{venta.fecha}"
    )
    qr_buffer = generar_qr(qr_data, size=100)
    qr_img = Image(qr_buffer, width=20 * mm, height=20 * mm)

    qr_table = Table([[qr_img]], colWidths=[ANCHO_POS - 6 * mm])
    qr_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.append(qr_table)

    elements.append(Spacer(1, 2 * mm))

    # ═══════════════════════════════════════════════════════════════════════
    # 7. MENSAJE FINAL
    # ═══════════════════════════════════════════════════════════════════════

    mensaje = empresa.get("mensaje_pie", "¡Gracias por su compra!")
    elements.append(
        HRFlowable(
            width=ANCHO_POS - 6 * mm,
            thickness=0.5,
            color=colors.black,
            spaceAfter=2 * mm,
        )
    )
    elements.append(Paragraph(mensaje, estilos["pos_titulo"]))
    elements.append(
        Paragraph(
            "Conserve este recibo como soporte de su transacción.", estilos["pos_dato"]
        )
    )
    elements.append(Spacer(1, 3 * mm))

    doc.build(elements)
    buffer.seek(0)
    return buffer
