# apps/dashboard/urls.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    URLs DEL DASHBOARD - ERP                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Todos los endpoints son GET (solo lectura).

Ruta base: /api/dashboard/

Endpoints disponibles:
══════════════════════════════════════════════════════════

  RESUMEN PRINCIPAL
  GET  /api/dashboard/resumen/
       → KPIs de tarjetas: ventas, compras, ganancia, clientes, alertas

  KPIs POR MÓDULO
  GET  /api/dashboard/ventas/
  GET  /api/dashboard/ventas/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
       → Métricas completas de ventas por período

  GET  /api/dashboard/compras/
  GET  /api/dashboard/compras/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
       → Métricas completas de compras por período

  GET  /api/dashboard/inventario/
       → Estado actual del inventario (stock, valores, por categoría)

  GET  /api/dashboard/clientes/
       → Métricas de la base de clientes

  GRÁFICOS
  GET  /api/dashboard/graficos/ventas/
  GET  /api/dashboard/graficos/ventas/?periodo=mes&agrupacion=dia
       → Datos para gráfico de ventas (periodo: semana|mes|año, agrupacion: dia|semana|mes)

  GET  /api/dashboard/graficos/compras/
  GET  /api/dashboard/graficos/compras/?periodo=mes&agrupacion=dia
       → Datos para gráfico de compras

  TOP RANKINGS
  GET  /api/dashboard/top/productos/
  GET  /api/dashboard/top/productos/?limite=10&fecha_inicio=...&fecha_fin=...
       → Top N productos más vendidos

  GET  /api/dashboard/top/clientes/
  GET  /api/dashboard/top/clientes/?limite=10&fecha_inicio=...&fecha_fin=...
       → Top N clientes por monto comprado

  ALERTAS Y ACTIVIDAD
  GET  /api/dashboard/alertas/
       → Alertas: sin stock, stock bajo, ventas pendientes

  GET  /api/dashboard/actividad/
  GET  /api/dashboard/actividad/?limite=20
       → Feed de últimas transacciones (ventas + compras)

══════════════════════════════════════════════════════════
"""

from django.urls import path
from apps.dashboard.views import (
    ResumenGeneralView,
    KpisVentasView,
    KpisComprasView,
    KpisInventarioView,
    KpisClientesView,
    GraficoVentasView,
    GraficoComprasView,
    ProductosTopView,
    ClientesTopView,
    AlertasView,
    ActividadRecienteView,
)

app_name = "dashboard"

urlpatterns = [
    # ── Resumen general ───────────────────────────────────────────────────────
    path("resumen/", ResumenGeneralView.as_view(), name="resumen-general"),
    # ── KPIs por módulo ───────────────────────────────────────────────────────
    path("ventas/", KpisVentasView.as_view(), name="kpis-ventas"),
    path("compras/", KpisComprasView.as_view(), name="kpis-compras"),
    path("inventario/", KpisInventarioView.as_view(), name="kpis-inventario"),
    path("clientes/", KpisClientesView.as_view(), name="kpis-clientes"),
    # ── Gráficos ──────────────────────────────────────────────────────────────
    path("graficos/ventas/", GraficoVentasView.as_view(), name="grafico-ventas"),
    path("graficos/compras/", GraficoComprasView.as_view(), name="grafico-compras"),
    # ── Top rankings ──────────────────────────────────────────────────────────
    path("top/productos/", ProductosTopView.as_view(), name="top-productos"),
    path("top/clientes/", ClientesTopView.as_view(), name="top-clientes"),
    # ── Alertas y actividad ───────────────────────────────────────────────────
    path("alertas/", AlertasView.as_view(), name="alertas"),
    path("actividad/", ActividadRecienteView.as_view(), name="actividad-reciente"),
]
