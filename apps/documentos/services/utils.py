# apps/documentos/services/utils.py
"""
🔧 UTILIDADES COMPARTIDAS PARA GENERACIÓN DE PDFs
==================================================

Funciones reutilizables por todos los servicios de documentos.
Incluye: QR, código de barras, estilos base, header/footer.

IMPORTANTE: Los datos de empresa (logo, nombre, NIT, etc.)
vienen del FRONTEND como parámetros. El backend NO los almacena.

Instalación requerida:
    pip install reportlab qrcode python-barcode pillow
"""

import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from PIL import Image as PILImage
from base64 import b64decode

from reportlab.lib import colors
from reportlab.lib.units import mm, inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import Image, Paragraph, Table, TableStyle, HRFlowable
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ============================================================================
# PALETA DE COLORES CORPORATIVA
# ============================================================================


class ColoresERP:
    """Paleta de colores estándar para documentos del ERP"""

    # Azul corporativo
    AZUL_PRINCIPAL = colors.HexColor("#1a365d")
    AZUL_CLARO = colors.HexColor("#2b6cb0")
    AZUL_FONDO = colors.HexColor("#ebf8ff")

    # Grises
    GRIS_OSCURO = colors.HexColor("#2d3748")
    GRIS_MEDIO = colors.HexColor("#718096")
    GRIS_CLARO = colors.HexColor("#e2e8f0")
    GRIS_FONDO = colors.HexColor("#f7fafc")

    # Semánticos
    VERDE_EXITO = colors.HexColor("#276749")
    ROJO_ERROR = colors.HexColor("#c53030")
    AMARILLO_ALERTA = colors.HexColor("#d69e2e")

    # Tabla
    HEADER_TABLA = colors.HexColor("#2b6cb0")
    FILA_PAR = colors.HexColor("#f7fafc")
    FILA_IMPAR = colors.white
    BORDE_TABLA = colors.HexColor("#cbd5e0")

    # POS térmico
    POS_NEGRO = colors.black
    POS_BLANCO = colors.white


# ============================================================================
# ESTILOS DE PÁRRAFO REUTILIZABLES
# ============================================================================


def obtener_estilos():
    """
    Devuelve diccionario de estilos de párrafo para documentos.

    Returns:
        dict: Estilos listos para usar en Paragraph()
    """
    base = getSampleStyleSheet()
    c = ColoresERP

    estilos = {
        # ── Empresa ──────────────────────────────────────
        "empresa_nombre": ParagraphStyle(
            "empresa_nombre",
            fontSize=16,
            fontName="Helvetica-Bold",
            textColor=c.AZUL_PRINCIPAL,
            spaceAfter=2,
        ),
        "empresa_dato": ParagraphStyle(
            "empresa_dato",
            fontSize=8,
            fontName="Helvetica",
            textColor=c.GRIS_OSCURO,
            spaceAfter=1,
        ),
        # ── Títulos de documento ─────────────────────────
        "titulo_doc": ParagraphStyle(
            "titulo_doc",
            fontSize=14,
            fontName="Helvetica-Bold",
            textColor=c.AZUL_PRINCIPAL,
            alignment=TA_RIGHT,
            spaceAfter=4,
        ),
        "numero_doc": ParagraphStyle(
            "numero_doc",
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=c.AZUL_CLARO,
            alignment=TA_RIGHT,
        ),
        "fecha_doc": ParagraphStyle(
            "fecha_doc",
            fontSize=8,
            fontName="Helvetica",
            textColor=c.GRIS_MEDIO,
            alignment=TA_RIGHT,
        ),
        # ── Etiquetas y valores ───────────────────────────
        "etiqueta": ParagraphStyle(
            "etiqueta",
            fontSize=7,
            fontName="Helvetica-Bold",
            textColor=c.GRIS_MEDIO,
            spaceAfter=1,
        ),
        "valor": ParagraphStyle(
            "valor",
            fontSize=9,
            fontName="Helvetica",
            textColor=c.GRIS_OSCURO,
        ),
        "valor_bold": ParagraphStyle(
            "valor_bold",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=c.GRIS_OSCURO,
        ),
        # ── Totales ───────────────────────────────────────
        "total_label": ParagraphStyle(
            "total_label",
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=c.AZUL_PRINCIPAL,
            alignment=TA_RIGHT,
        ),
        "total_valor": ParagraphStyle(
            "total_valor",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=c.VERDE_EXITO,
            alignment=TA_RIGHT,
        ),
        # ── Legal / Footer ────────────────────────────────
        "texto_legal": ParagraphStyle(
            "texto_legal",
            fontSize=6,
            fontName="Helvetica",
            textColor=c.GRIS_MEDIO,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=7,
            fontName="Helvetica",
            textColor=c.GRIS_MEDIO,
            alignment=TA_CENTER,
        ),
        # ── POS Térmico ───────────────────────────────────
        "pos_titulo": ParagraphStyle(
            "pos_titulo",
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "pos_empresa": ParagraphStyle(
            "pos_empresa",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=1,
        ),
        "pos_dato": ParagraphStyle(
            "pos_dato",
            fontSize=8,
            fontName="Helvetica",
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=1,
        ),
        "pos_normal": ParagraphStyle(
            "pos_normal",
            fontSize=8,
            fontName="Helvetica",
            textColor=colors.black,
            alignment=TA_LEFT,
        ),
        "pos_bold": ParagraphStyle(
            "pos_bold",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=colors.black,
            alignment=TA_LEFT,
        ),
        "pos_total": ParagraphStyle(
            "pos_total",
            fontSize=11,
            fontName="Helvetica-Bold",
            textColor=colors.black,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
    }

    return estilos


# ============================================================================
# GENERADORES DE IMÁGENES
# ============================================================================


def generar_qr(data: str, size: int = 200) -> BytesIO:
    """
    Genera imagen QR en memoria.

    Args:
        data: Texto/URL a codificar
        size: Tamaño en píxeles

    Returns:
        BytesIO: Imagen PNG en memoria

    Ejemplo:
        qr = generar_qr("COMP-00001|$1500.00|2026-02-17")
        elements.append(Image(qr, width=1.5*inch, height=1.5*inch))
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generar_codigo_barras(numero: str) -> BytesIO:
    """
    Genera código de barras CODE128 en memoria.

    Args:
        numero: Número/texto a codificar

    Returns:
        BytesIO: Imagen PNG en memoria

    Ejemplo:
        bc = generar_codigo_barras("COMP-00001")
        elements.append(Image(bc, width=3*inch, height=0.8*inch))
    """
    buffer = BytesIO()

    options = {
        "module_width": 0.3,
        "module_height": 8.0,
        "quiet_zone": 2,
        "font_size": 8,
        "text_distance": 3,
        "write_text": True,
    }

    codigo = barcode.get("code128", str(numero), writer=ImageWriter())
    codigo.write(buffer, options=options)
    buffer.seek(0)
    return buffer


def procesar_logo(logo_base64: str) -> BytesIO | None:
    """
    Procesa logo enviado desde el frontend como base64.

    El frontend envía el logo como base64 porque el backend
    NO almacena datos de empresa.

    Args:
        logo_base64: String base64 del logo (puede incluir data:image/png;base64,)

    Returns:
        BytesIO: Imagen procesada o None si no hay logo

    Ejemplo desde frontend:
        { "logo_base64": "data:image/png;base64,iVBORw0KGgo..." }
    """
    if not logo_base64:
        return None

    try:
        # Limpiar prefijo si viene con él
        if "base64," in logo_base64:
            logo_base64 = logo_base64.split("base64,")[1]

        img_data = b64decode(logo_base64)
        buffer = BytesIO(img_data)

        # Validar que es imagen válida
        PILImage.open(buffer).verify()
        buffer.seek(0)

        return buffer
    except Exception:
        return None


# ============================================================================
# COMPONENTES REUTILIZABLES
# ============================================================================


def construir_header_empresa(
    empresa: dict, doc_titulo: str, doc_numero: str, doc_fecha: str
) -> Table:
    """
    Construye el header estándar de todos los documentos A4.

    Layout:
    ┌─────────────────────────────┬──────────────────────┐
    │  [LOGO]  Nombre empresa     │   TÍTULO DOCUMENTO   │
    │          NIT: xxx           │   Número: COMP-00001 │
    │          Dirección          │   Fecha: 2026-02-17  │
    │          Tel / Email        │                      │
    └─────────────────────────────┴──────────────────────┘

    Args:
        empresa: dict con {nombre, nit, direccion, telefono, email, logo_base64, ciudad, regimen}
        doc_titulo: Ej: "ORDEN DE COMPRA"
        doc_numero: Ej: "COMP-00001"
        doc_fecha: Ej: "17 de febrero de 2026"

    Returns:
        Table: Componente listo para agregar a elements[]
    """
    estilos = obtener_estilos()

    # ── Columna izquierda: empresa ────────────────────────────────────────
    col_empresa = []

    # Logo (si viene del frontend)
    logo_buffer = procesar_logo(empresa.get("logo_base64", ""))
    if logo_buffer:
        col_empresa.append(Image(logo_buffer, width=1.8 * inch, height=0.8 * inch))

    col_empresa.append(
        Paragraph(empresa.get("nombre", "EMPRESA"), estilos["empresa_nombre"])
    )

    if empresa.get("nit"):
        col_empresa.append(Paragraph(f"NIT: {empresa['nit']}", estilos["empresa_dato"]))
    if empresa.get("regimen"):
        col_empresa.append(Paragraph(empresa["regimen"], estilos["empresa_dato"]))
    if empresa.get("direccion"):
        col_empresa.append(
            Paragraph(f"Dir: {empresa['direccion']}", estilos["empresa_dato"])
        )
    if empresa.get("ciudad"):
        col_empresa.append(Paragraph(empresa["ciudad"], estilos["empresa_dato"]))
    if empresa.get("telefono"):
        col_empresa.append(
            Paragraph(f"Tel: {empresa['telefono']}", estilos["empresa_dato"])
        )
    if empresa.get("email"):
        col_empresa.append(Paragraph(empresa["email"], estilos["empresa_dato"]))

    # ── Columna derecha: info del documento ────────────────────────────────
    col_doc = [
        Paragraph(doc_titulo, estilos["titulo_doc"]),
        Paragraph(doc_numero, estilos["numero_doc"]),
        Paragraph(doc_fecha, estilos["fecha_doc"]),
    ]

    # ── Tabla de 2 columnas ────────────────────────────────────────────────
    header_table = Table(
        [[col_empresa, col_doc]],
        colWidths=["60%", "40%"],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    return header_table


def construir_tabla_productos(detalles: list, es_pos: bool = False) -> Table:
    """
    Construye tabla de productos estilizada.

    Args:
        detalles: Lista de dicts con {codigo, nombre, cantidad, precio, subtotal}
        es_pos: Si es True, formato compacto para ticket térmico

    Returns:
        Table: Tabla con estilos aplicados
    """
    c = ColoresERP

    if es_pos:
        # ── Formato POS ───────────────────────────────────────────────────
        data = [["Producto", "Cant", "P.Unit", "Total"]]

        for d in detalles:
            data.append(
                [
                    str(d.get("nombre", ""))[:20],  # Truncar para ticket
                    str(d.get("cantidad", 0)),
                    f"${float(d.get('precio', 0)):,.0f}",
                    f"${float(d.get('subtotal', 0)):,.0f}",
                ]
            )

        tabla = Table(data, colWidths=["40%", "15%", "20%", "25%"])
        tabla.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                    ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.black),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )

    else:
        # ── Formato A4 completo ───────────────────────────────────────────
        data = [["Código", "Descripción", "Cant.", "Precio Unit.", "Subtotal"]]

        for i, d in enumerate(detalles):
            data.append(
                [
                    str(d.get("codigo", "-")),
                    str(d.get("nombre", "")),
                    str(d.get("cantidad", 0)),
                    f"${float(d.get('precio', 0)):,.2f}",
                    f"${float(d.get('subtotal', 0)):,.2f}",
                ]
            )

        tabla = Table(
            data,
            colWidths=["12%", "42%", "10%", "18%", "18%"],
        )
        tabla.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), c.HEADER_TABLA),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    # Filas
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 1), (1, -1), "LEFT"),
                    # Alternado
                    *[
                        (
                            "BACKGROUND",
                            (0, i),
                            (-1, i),
                            c.FILA_PAR if i % 2 == 0 else c.FILA_IMPAR,
                        )
                        for i in range(1, len(data))
                    ],
                    # Bordes
                    ("GRID", (0, 0), (-1, -1), 0.3, c.BORDE_TABLA),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, c.HEADER_TABLA),
                    # Padding
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [c.FILA_IMPAR, c.FILA_PAR]),
                ]
            )
        )

    return tabla


def construir_tabla_totales(
    subtotal: float, descuento: float = 0, iva_pct: float = 0, total: float = 0
) -> Table:
    """
    Construye tabla de totales alineada a la derecha.

    Args:
        subtotal: Subtotal antes de impuestos
        descuento: Descuento aplicado
        iva_pct: Porcentaje de IVA (ej: 19 para 19%)
        total: Total final

    Returns:
        Table: Tabla de totales
    """
    c = ColoresERP
    estilos = obtener_estilos()

    iva_valor = subtotal * (iva_pct / 100) if iva_pct > 0 else 0

    filas = []

    filas.append(
        [
            Paragraph("Subtotal:", estilos["etiqueta"]),
            Paragraph(f"${subtotal:,.2f}", estilos["valor"]),
        ]
    )

    if descuento > 0:
        filas.append(
            [
                Paragraph("Descuento:", estilos["etiqueta"]),
                Paragraph(
                    f"-${descuento:,.2f}",
                    ParagraphStyle(
                        "descuento",
                        fontSize=9,
                        textColor=c.ROJO_ERROR,
                        alignment=TA_RIGHT,
                    ),
                ),
            ]
        )

    if iva_pct > 0:
        filas.append(
            [
                Paragraph(f"IVA ({iva_pct:.0f}%):", estilos["etiqueta"]),
                Paragraph(f"${iva_valor:,.2f}", estilos["valor"]),
            ]
        )

    filas.append(
        [
            Paragraph("TOTAL:", estilos["total_label"]),
            Paragraph(f"${total:,.2f}", estilos["total_valor"]),
        ]
    )

    tabla = Table(filas, colWidths=["60%", "40%"])
    tabla.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("LINEABOVE", (0, -1), (-1, -1), 1.5, c.AZUL_PRINCIPAL),
                ("TOPPADDING", (0, -1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return tabla


def construir_footer(empresa: dict, texto_extra: str = "") -> list:
    """
    Construye el footer estándar de documentos.

    Args:
        empresa: dict con datos de empresa
        texto_extra: Texto adicional (ej: texto legal de factura)

    Returns:
        list: Elementos para agregar a elements[]
    """
    estilos = obtener_estilos()
    footer_elements = []

    footer_elements.append(
        HRFlowable(
            width="100%", thickness=0.5, color=ColoresERP.GRIS_CLARO, spaceAfter=6
        )
    )

    if texto_extra:
        footer_elements.append(Paragraph(texto_extra, estilos["texto_legal"]))

    footer_elements.append(
        Paragraph(
            f"Documento generado por {empresa.get('nombre', 'ERP')} · "
            f"Este documento es de carácter informativo.",
            estilos["footer"],
        )
    )

    return footer_elements


def formatear_fecha(fecha_input, formato: str = "largo") -> str:
    """
    Formatea fecha ISO a formato legible en español.

    Args:
        fecha_input: Fecha en formato string ISO, datetime, o date
        formato: "largo" → "12 de abril de 2026"
                 "corto" → "12/Abr/2026 5:14 PM"
                 "fecha" → "12/04/2026"

    Returns:
        str: Fecha formateada en español

    Ejemplo:
        formatear_fecha("2026-04-12T21:58:23+00:00")          → "12 de abril de 2026"
        formatear_fecha("2026-04-12T21:58:23+00:00", "corto") → "12/Abr/2026 9:58 PM"
        formatear_fecha(venta.fecha)                           → "12 de abril de 2026"
    """
    from datetime import datetime, date

    meses_largo = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]

    meses_corto = [
        "",
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
        "Sep",
        "Oct",
        "Nov",
        "Dic",
    ]

    try:
        # Si ya es datetime o date, usarlo directamente
        if isinstance(fecha_input, datetime):
            fecha = fecha_input
        elif isinstance(fecha_input, date):
            fecha = datetime(fecha_input.year, fecha_input.month, fecha_input.day)
        elif isinstance(fecha_input, str) and fecha_input:
            # Limpiar string: quitar timezone info para parsing simple
            fecha_str = str(fecha_input).strip()
            if "T" in fecha_str:
                # Quitar timezone offset (+00:00, -05:00, Z, etc.)
                base = fecha_str.split("+")[0].split("Z")[0]
                # Truncar microsegundos excesivos
                if "." in base:
                    partes = base.split(".")
                    base = f"{partes[0]}.{partes[1][:6]}"
                fecha = datetime.fromisoformat(base)
            elif " " in fecha_str and ":" in fecha_str:
                # Formato "2026-04-12 21:58:23.081726+00:00"
                base = fecha_str.split("+")[0].split("Z")[0].strip()
                if "." in base:
                    partes = base.split(".")
                    base = f"{partes[0]}.{partes[1][:6]}"
                fecha = datetime.fromisoformat(base)
            else:
                fecha = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
        else:
            return str(fecha_input) if fecha_input else ""

        if formato == "corto":
            hora = fecha.strftime("%-I:%M %p") if hasattr(fecha, 'hour') else ""
            # Windows no soporta %-I, usar alternativa
            try:
                hora = fecha.strftime("%-I:%M %p")
            except ValueError:
                hora = fecha.strftime("%I:%M %p").lstrip("0")
            return f"{fecha.day}/{meses_corto[fecha.month]}/{fecha.year} {hora}".strip()

        elif formato == "fecha":
            return f"{fecha.day:02d}/{fecha.month:02d}/{fecha.year}"

        else:  # "largo"
            return f"{fecha.day} de {meses_largo[fecha.month]} de {fecha.year}"

    except Exception:
        return str(fecha_input) if fecha_input else ""


def numero_a_letras(numero: float) -> str:
    """
    Convierte número a texto en español (para facturas).

    Args:
        numero: Número a convertir

    Returns:
        str: Ej: "UN MILLÓN QUINIENTOS MIL PESOS M/CTE"
    """
    # Implementación básica
    try:
        entero = int(numero)
        decimales = round((numero - entero) * 100)

        unidades = [
            "",
            "UN",
            "DOS",
            "TRES",
            "CUATRO",
            "CINCO",
            "SEIS",
            "SIETE",
            "OCHO",
            "NUEVE",
            "DIEZ",
            "ONCE",
            "DOCE",
            "TRECE",
            "CATORCE",
            "QUINCE",
            "DIECISÉIS",
            "DIECISIETE",
            "DIECIOCHO",
            "DIECINUEVE",
        ]
        decenas = [
            "",
            "",
            "VEINTE",
            "TREINTA",
            "CUARENTA",
            "CINCUENTA",
            "SESENTA",
            "SETENTA",
            "OCHENTA",
            "NOVENTA",
        ]

        def bloque(n):
            if n == 0:
                return ""
            elif n < 20:
                return unidades[n]
            elif n < 100:
                resto = n % 10
                base = decenas[n // 10]
                return base if resto == 0 else f"{base} Y {unidades[resto]}"
            elif n < 1000:
                cientos = n // 100
                resto = n % 100
                prefijos = [
                    "",
                    "CIEN",
                    "DOSCIENTOS",
                    "TRESCIENTOS",
                    "CUATROCIENTOS",
                    "QUINIENTOS",
                    "SEISCIENTOS",
                    "SETECIENTOS",
                    "OCHOCIENTOS",
                    "NOVECIENTOS",
                ]
                if resto == 0:
                    return prefijos[cientos]
                elif cientos == 1:
                    return f"CIENTO {bloque(resto)}"
                else:
                    return f"{prefijos[cientos]} {bloque(resto)}"
            else:
                miles = n // 1000
                resto = n % 1000
                pref = "UN MIL" if miles == 1 else f"{bloque(miles)} MIL"
                return pref if resto == 0 else f"{pref} {bloque(resto)}"

        if entero >= 1_000_000:
            millones = entero // 1_000_000
            resto = entero % 1_000_000
            pref = "UN MILLÓN" if millones == 1 else f"{bloque(millones)} MILLONES"
            texto = pref if resto == 0 else f"{pref} {bloque(resto)}"
        else:
            texto = bloque(entero) if entero > 0 else "CERO"

        if decimales > 0:
            return f"{texto} CON {decimales:02d}/100 PESOS M/CTE"
        return f"{texto} PESOS M/CTE"

    except Exception:
        return f"${numero:,.2f} PESOS M/CTE"
