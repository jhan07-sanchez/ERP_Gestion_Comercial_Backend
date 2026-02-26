# apps/inventario/urls.py
"""
URLs para la app de Inventario

Este archivo define las rutas de la API para:
- Inventario (stock)
- Movimientos de Inventario

Estructura modular siguiendo el patrón de arquitectura por dominio.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventario.views import (
    InventarioViewSet,
    MovimientoInventarioViewSet
)

app_name = 'inventario'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'inventarios', InventarioViewSet, basename='inventario')
router.register(r'movimientos', MovimientoInventarioViewSet, basename='movimiento')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

INVENTARIOS:
────────────
Básicas (Solo lectura):
  GET    /api/inventario/inventarios/                  - Listar inventarios
  GET    /api/inventario/inventarios/{id}/             - Ver detalle

Acciones personalizadas:
  GET    /api/inventario/inventarios/estadisticas/     - Estadísticas generales

Filtros disponibles:
  ?stock_bajo=true         - Solo productos con stock bajo
  ?categoria=Ropa          - Filtrar por categoría
  ?solo_activos=true       - Solo productos activos

MOVIMIENTOS:
────────────
Básicas:
  GET    /api/inventario/movimientos/                  - Listar movimientos
  POST   /api/inventario/movimientos/                  - Registrar movimiento
  GET    /api/inventario/movimientos/{id}/             - Ver detalle

Acciones personalizadas:
  GET    /api/inventario/movimientos/resumen/          - Resumen de movimientos

Filtros disponibles:
  ?producto_id=1           - Filtrar por producto
  ?tipo=ENTRADA            - Filtrar por tipo (ENTRADA/SALIDA)
  ?referencia=COMPRA-001   - Filtrar por referencia
  ?usuario_id=1            - Filtrar por usuario
  ?fecha_inicio=2026-01-01 - Fecha inicial
  ?fecha_fin=2026-01-31    - Fecha final

═══════════════════════════════════════════════════════════════════════════
"""