# apps/documentos/urls.py
"""
🔗 URLS DEL MÓDULO DOCUMENTOS
==============================

Endpoints disponibles:
    POST  /api/documentos/compra/{id}/pdf/
    POST  /api/documentos/venta/{id}/factura/
    POST  /api/documentos/venta/{id}/recibo-pos/
    POST  /api/documentos/reportes/ventas/
    POST  /api/documentos/reportes/compras/
    POST  /api/documentos/reportes/inventario/
"""

from django.urls import path
from .views import (
    CompraDocumentoView,
    VentaFacturaView,
    VentaReciboPosView,
    ReporteVentasView,
    ReporteComprasView,
    ReporteInventarioView,
)

app_name = "documentos"

urlpatterns = [
    # ── Compras ───────────────────────────────────────────────────
    path(
        "compra/<int:pk>/pdf/",
        CompraDocumentoView.as_view(),
        name="compra-pdf",
    ),
    # ── Ventas ────────────────────────────────────────────────────
    path(
        "venta/<int:pk>/factura/",
        VentaFacturaView.as_view(),
        name="venta-factura",
    ),
    path(
        "venta/<int:pk>/recibo-pos/",
        VentaReciboPosView.as_view(),
        name="venta-recibo-pos",
    ),
    # ── Reportes ──────────────────────────────────────────────────
    path(
        "reportes/ventas/",
        ReporteVentasView.as_view(),
        name="reporte-ventas",
    ),
    path(
        "reportes/compras/",
        ReporteComprasView.as_view(),
        name="reporte-compras",
    ),
    path(
        "reportes/inventario/",
        ReporteInventarioView.as_view(),
        name="reporte-inventario",
    ),
]
