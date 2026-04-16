# apps/documentos/services/recibo_pos.py
"""
🧾 GENERADOR - RECIBO POS TÉRMICO (80mm) — Versión Empresarial
=============================================================

Genera recibo para impresora térmica de 80mm con altura dinámica real.
Optimizado para que quepa SIEMPRE en una sola página continua.

Mejoras v2:
- Altura dinámica calculada por bloques reales.
- QR profesional con JSON serializado.
- Fechas legibles (formato corto).
- Soporte para nombres largos en productos.
- Incluye hash de verificación e integridad.
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
from reportlab.lib.units import mm, inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from .utils import (
    obtener_estilos,
    generar_qr,
    formatear_fecha,
    procesar_logo,
)


# Ancho estándar rollo 80mm (área imprimible ~72mm)
# 80mm = ~227 puntos. Usamos 72mm para dejar margen físico seguro.
ANCHO_POS = 72 * mm


def _calcular_altura_dinamica(num_productos: int, empresa_lines: int = 5, tiene_logo: bool = False) -> float:
    """
    Calcula la altura física necesaria del ticket para evitar saltos de página.
    
    Estimación de bloques en mm:
    - Logo: 12mm (si existe)
    - Empresa: 4mm por línea (nombre, nit, dir, tel, email)
    - Título y Número: 20mm
    - Fecha y Cliente: 18mm
    - Header Tabla: 8mm
    - Productos: 10mm por producto (nombre + línea de cálculo)
    - Totales: 25mm
    - Pago y Cambio: 12mm
    - QR: 30mm
    - Footer/Mensaje: 15mm
    - Margen seguridad: 15mm
    """
    altura = 135 * mm # Base mínima sin productos
    if tiene_logo:
        altura += 12 * mm
    
    altura += (empresa_lines * 4) * mm
    altura += (num_productos * 10) * mm
    altura += 15 * mm # Margen de seguridad extra
    
    return altura


def generar_recibo_pos(documento, empresa: dict) -> BytesIO:
    """
    Genera recibo POS optimizado para 80mm desde el modelo Documento.
    """
    buffer = BytesIO()
    estilos = obtener_estilos()

    # 1. Obtener datos de origen
    venta = documento.venta
    if not venta:
        raise ValueError("El documento no está asociado a una venta.")

    # 2. Preparar datos
    # Usamos las líneas persistentes (snapshot)
    lineas = list(documento.lineas.all().order_by("orden"))
    
    # Contar líneas de empresa útiles
    emp_keys = ["nit", "direccion", "ciudad", "telefono", "email"]
    empresa_lines = len([k for k in emp_keys if empresa.get(k)])
    logo_buffer = procesar_logo(empresa.get("logo_base64", ""))
    
    altura = _calcular_altura_dinamica(
        len(lineas), 
        empresa_lines=empresa_lines, 
        tiene_logo=bool(logo_buffer)
    )

    numero = documento.numero_interno

    doc = SimpleDocTemplate(
        buffer,
        pagesize=(ANCHO_POS, altura),
        rightMargin=3 * mm,
        leftMargin=3 * mm,
        topMargin=4 * mm,
        bottomMargin=4 * mm,
        title=f"Recibo {numero}",
    )

    elements = []

    # ── 1. LOGO ───────────────────────────────────────────────────────────
    if logo_buffer:
        logo_img = Image(logo_buffer, width=18 * mm, height=10 * mm)
        logo_table = Table([[logo_img]], colWidths=[ANCHO_POS - 6 * mm])
        logo_table.setStyle(TableStyle([
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(logo_table)

    # ── 2. HEADER EMPRESA ──────────────────────────────────────────────────
    elements.append(Paragraph(empresa.get("nombre", "EMPRESA").upper(), estilos["pos_empresa"]))

    if empresa.get("nit"):
        elements.append(Paragraph(f"NIT: {empresa['nit']}", estilos["pos_dato"]))
    if empresa.get("direccion"):
        elements.append(Paragraph(empresa["direccion"], estilos["pos_dato"]))
    if empresa.get("ciudad"):
        elements.append(Paragraph(empresa["ciudad"], estilos["pos_dato"]))
    if empresa.get("telefono"):
        elements.append(Paragraph(f"Tel: {empresa['telefono']}", estilos["pos_dato"]))
    if empresa.get("email"):
        elements.append(Paragraph(empresa["email"], estilos["pos_dato"]))

    elements.append(Spacer(1, 1.5 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.8, color=colors.black, spaceAfter=1.5 * mm))

    # ── 3. DATOS DEL RECIBO ───────────────────────────────────────────────
    elements.append(Paragraph("RECIBO DE VENTA", estilos["pos_titulo"]))
    elements.append(Paragraph(f"<b>N° {numero}</b>", estilos["pos_empresa"]))
    
    # Fecha de emisión del documento
    fecha_formateada = formatear_fecha(documento.fecha_emision, formato="corto")
    elements.append(Paragraph(fecha_formateada, estilos["pos_dato"]))

    elements.append(Spacer(1, 1.5 * mm))
    
    # Datos del Cliente
    cliente = venta.cliente
    nombre_cliente = getattr(cliente, "nombre", str(cliente))
    elements.append(Paragraph(f"CLIENTE: {nombre_cliente[:30]}", estilos["pos_bold"]))
    if getattr(cliente, "documento", None):
        elements.append(Paragraph(f"NIT/CC: {cliente.documento}", estilos["pos_normal"]))

    elements.append(Spacer(1, 1.5 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=1.5 * mm))

    # ── 4. TABLA DE PRODUCTOS (Snapshot) ──────────────────────────────────
    # Header compacto
    elements.append(Paragraph("DESCRIPCIÓN      CANT      TOTAL", estilos["pos_bold"]))
    elements.append(HRFlowable(width="100%", thickness=0.3, color=colors.black, spaceAfter=1 * mm))

    for d in lineas:
        precio = float(d.precio_unitario)
        cantidad = float(d.cantidad)
        sub = float(d.subtotal)

        # Nombre con soporte para 2 líneas si es largo
        elements.append(Paragraph(d.descripcion, estilos["pos_bold"]))

        # Línea de cálculo: "  1 x $2,000,000      $2,000,000"
        linea_data = [
            Paragraph(f"  {cantidad:.0f} x ${precio:,.0f}", estilos["pos_normal"]),
            Paragraph(f"${sub:,.0f}", ParagraphStyle("pr", parent=estilos["pos_normal"], alignment=TA_RIGHT))
        ]
        t_linea = Table([linea_data], colWidths=[(ANCHO_POS-6*mm)*0.65, (ANCHO_POS-6*mm)*0.35])
        t_linea.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ]))
        elements.append(t_linea)

    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceBefore=1 * mm, spaceAfter=1.5 * mm))

    # ── 5. TOTALES ────────────────────────────────────────────────────────
    total_final = float(documento.total)
    subtotal_acu = float(documento.subtotal)
    # IVA e impuestos
    iva_valor = float(documento.impuestos)
    descuento = float(getattr(venta, "descuento", 0) or 0)
    
    def add_total_line(label, value, is_bold=False):
        style_l = estilos["pos_bold"] if is_bold else estilos["pos_normal"]
        style_r = ParagraphStyle("pr", parent=style_l, alignment=TA_RIGHT, fontSize=11 if is_bold else 8)
        
        t = Table([[Paragraph(label, style_l), Paragraph(f"${value:,.0f}", style_r)]], 
                  colWidths=[(ANCHO_POS-6*mm)*0.55, (ANCHO_POS-6*mm)*0.45])
        t.setStyle(TableStyle([
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
        ]))
        elements.append(t)

    add_total_line("Subtotal:", subtotal_acu)
    if descuento > 0:
        add_total_line("Descuento:", -descuento)
    if iva_valor > 0:
        add_total_line("Impuestos:", iva_valor)
    
    elements.append(Spacer(1, 1 * mm))
    add_total_line("TOTAL:", total_final, is_bold=True)
    elements.append(Spacer(1, 2 * mm))

    # Forma de pago
    metodo = getattr(venta, "metodo_pago", "EFECTIVO")
    elements.append(Paragraph(f"FORMA DE PAGO: {metodo}", estilos["pos_bold"]))
    
    # Manejo de Efectivo/Cambio
    recibido = float(getattr(venta, "efectivo_recibido", 0) or 0)
    if recibido > 0:
        cambio = recibido - total_final
        add_total_line("Efectivo:", recibido)
        if cambio >= 0:
            add_total_line("Cambio:", cambio, is_bold=True)

    elements.append(Spacer(1, 3 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=2 * mm))

    # ── 6. QR PROFESIONAL (JSON) ──────────────────────────────────────────
    hash_doc = documento.codigo_verificacion or "-"

    qr_payload = {
        "num": numero,
        "nit": empresa.get("nit", ""),
        "tot": total_final,
        "fec": str(documento.fecha_emision)[:19],
        "hash": hash_doc
    }
    qr_data = json.dumps(qr_payload)
    qr_buffer = generar_qr(qr_data, size=120)
    qr_img = Image(qr_buffer, width=25 * mm, height=25 * mm)
    
    qr_table = Table([[qr_img]], colWidths=[ANCHO_POS - 6 * mm])
    qr_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    elements.append(qr_table)

    elements.append(Spacer(1, 2 * mm))

    # ── 7. FOOTER ─────────────────────────────────────────────────────────
    mensaje = empresa.get("mensaje_pie", "¡Gracias por su compra!")
    elements.append(Paragraph(mensaje.upper(), estilos["pos_titulo"]))
    elements.append(Paragraph("Conserve este recibo como soporte.", estilos["pos_dato"]))
    
    if hash_doc != "-":
        verify_style = ParagraphStyle("vd", parent=estilos["pos_normal"], fontSize=6, alignment=TA_CENTER)
        elements.append(Paragraph(f"Verificación: {hash_doc}", verify_style))

    elements.append(Spacer(1, 4 * mm))

    # Generar PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

