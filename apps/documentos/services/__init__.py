# apps/documentos/services/__init__.py
"""
📦 MÓDULO DE SERVICIOS - DOCUMENTOS ERP — Versión Empresarial
"""

from .pdf_compra import generar_pdf_compra
from .pdf_factura import generar_pdf_factura
from .recibo_pos import generar_recibo_pos
from .pdf_reporte import (
    generar_reporte_ventas,
    generar_reporte_compras,
    generar_reporte_inventario,
)
from .utils import (
    generar_qr,
    generar_codigo_barras,
    formatear_fecha,
    numero_a_letras,
)
from .documento_service import DocumentoService
from .numeracion_service import NumeracionService

__all__ = [
    "generar_pdf_compra",
    "generar_pdf_factura",
    "generar_recibo_pos",
    "generar_reporte_ventas",
    "generar_reporte_compras",
    "generar_reporte_inventario",
    "generar_qr",
    "generar_codigo_barras",
    "formatear_fecha",
    "numero_a_letras",
    "DocumentoService",
    "NumeracionService",
]
