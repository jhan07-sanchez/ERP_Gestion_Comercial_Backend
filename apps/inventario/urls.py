# apps/inventario/urls.py
"""
URLs para la app de Inventario

Este archivo define las rutas de la API para:
- Productos
- Categorías
- Inventario
- Movimientos de Inventario

Estructura modular siguiendo el patrón de apps/usuarios
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.inventario.views import (
    ProductoViewSet,
    CategoriaViewSet,
    InventarioViewSet,
    MovimientoInventarioViewSet
)

app_name = 'inventario'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'productos', ProductoViewSet, basename='producto')
router.register(r'categorias', CategoriaViewSet, basename='categoria')
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

PRODUCTOS:
──────────
Básicas:
  GET    /api/inventario/productos/                    - Listar productos
  POST   /api/inventario/productos/                    - Crear producto
  GET    /api/inventario/productos/{id}/               - Ver detalle
  PUT    /api/inventario/productos/{id}/               - Actualizar completo
  PATCH  /api/inventario/productos/{id}/               - Actualizar parcial
  DELETE /api/inventario/productos/{id}/               - Eliminar

Acciones personalizadas:
  GET    /api/inventario/productos/stock_bajo/         - Productos con stock bajo
  POST   /api/inventario/productos/{id}/activar/       - Activar producto
  POST   /api/inventario/productos/{id}/desactivar/    - Desactivar producto
  GET    /api/inventario/productos/{id}/movimientos/   - Historial de movimientos
  GET    /api/inventario/productos/{id}/estadisticas/  - Estadísticas del producto
  POST   /api/inventario/productos/{id}/ajustar_stock/ - Ajustar stock manualmente

Filtros disponibles:
  ?categoria_id=1          - Filtrar por ID de categoría
  ?categoria=Electrónica   - Filtrar por nombre de categoría
  ?estado=true             - Filtrar por estado (activo/inactivo)
  ?precio_min=1000         - Precio mínimo
  ?precio_max=50000        - Precio máximo
  ?search=laptop           - Búsqueda general (código, nombre, descripción)

CATEGORÍAS:
───────────
Básicas:
  GET    /api/inventario/categorias/                   - Listar categorías
  POST   /api/inventario/categorias/                   - Crear categoría
  GET    /api/inventario/categorias/{id}/              - Ver detalle
  PUT    /api/inventario/categorias/{id}/              - Actualizar completo
  PATCH  /api/inventario/categorias/{id}/              - Actualizar parcial
  DELETE /api/inventario/categorias/{id}/              - Eliminar

Acciones personalizadas:
  GET    /api/inventario/categorias/{id}/productos/    - Productos de la categoría
  GET    /api/inventario/categorias/{id}/estadisticas/ - Estadísticas de la categoría

Filtros disponibles:
  ?nombre=Electrónica      - Filtrar por nombre
  ?search=electro          - Búsqueda general (nombre, descripción)

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
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════════════

1. Crear un producto:
   POST /api/inventario/productos/
   {
     "codigo": "PROD001",
     "nombre": "Laptop HP",
     "descripcion": "Laptop HP Pavilion 15 pulgadas",
     "categoria": 1,
     "precio_compra": 1500000,
     "precio_venta": 2000000,
     "fecha_ingreso": "2026-01-28",
     "stock_minimo": 5,
     "estado": true
   }

2. Registrar entrada de inventario:
   POST /api/inventario/movimientos/
   {
     "producto": 1,
     "tipo_movimiento": "ENTRADA",
     "cantidad": 50,
     "referencia": "COMPRA-001"
   }

3. Registrar salida de inventario:
   POST /api/inventario/movimientos/
   {
     "producto": 1,
     "tipo_movimiento": "SALIDA",
     "cantidad": 10,
     "referencia": "VENTA-001"
   }

4. Ver productos con stock bajo:
   GET /api/inventario/productos/stock_bajo/

5. Ver estadísticas de inventario:
   GET /api/inventario/inventarios/estadisticas/

6. Ajustar stock manualmente:
   POST /api/inventario/productos/1/ajustar_stock/
   {
     "stock_nuevo": 100,
     "motivo": "Ajuste por inventario físico"
   }

═══════════════════════════════════════════════════════════════════════════
"""