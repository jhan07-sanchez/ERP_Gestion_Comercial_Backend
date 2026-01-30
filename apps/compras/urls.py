# apps/compras/urls.py
"""
URLs para la app de Compras

Este archivo define las rutas de la API para:
- Compras
- Detalles de Compra

Estructura modular siguiendo el patrón de apps/usuarios, apps/inventario y apps/ventas
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.compras.views import CompraViewSet, DetalleCompraViewSet

app_name = 'compras'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'compras', CompraViewSet, basename='compra')
router.register(r'detalles', DetalleCompraViewSet, basename='detalle')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

COMPRAS:
────────
Básicas:
  GET    /api/compras/compras/                    - Listar compras
  POST   /api/compras/compras/                    - Crear compra
  GET    /api/compras/compras/{id}/               - Ver detalle
  PUT    /api/compras/compras/{id}/               - Actualizar completo
  PATCH  /api/compras/compras/{id}/               - Actualizar parcial
  DELETE /api/compras/compras/{id}/               - Eliminar

Acciones personalizadas:
  POST   /api/compras/compras/{id}/anular/        - Anular compra
  GET    /api/compras/compras/{id}/estadisticas/  - Estadísticas de la compra
  GET    /api/compras/compras/resumen/            - Resumen general
  GET    /api/compras/compras/por_proveedor/      - Compras por proveedor

Filtros disponibles:
  ?proveedor=ProveedorXYZ    - Filtrar por nombre de proveedor
  ?usuario_id=1              - Filtrar por ID de usuario
  ?fecha_inicio=2026-01-01   - Fecha inicial
  ?fecha_fin=2026-01-31      - Fecha final
  ?total_min=100000          - Total mínimo
  ?total_max=500000          - Total máximo
  ?search=ABC                - Búsqueda general (proveedor, ID)

DETALLES DE COMPRA:
───────────────────
Básicas (Solo lectura):
  GET    /api/compras/detalles/                   - Listar detalles
  GET    /api/compras/detalles/{id}/              - Ver detalle

Filtros disponibles:
  ?compra_id=1               - Filtrar por ID de compra
  ?producto_id=1             - Filtrar por ID de producto

═══════════════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════════════

1. Crear una compra:
   POST /api/compras/compras/
   {
     "proveedor": "Proveedor ABC S.A.S.",
     "detalles": [
       {
         "producto_id": 1,
         "cantidad": 50,
         "precio_compra": 1800000
       },
       {
         "producto_id": 2,
         "cantidad": 100,
         "precio_compra": 75000
       }
     ]
   }

2. Anular una compra:
   POST /api/compras/compras/1/anular/
   {
     "motivo": "Error en los precios, se debe registrar nuevamente"
   }

3. Ver estadísticas de una compra:
   GET /api/compras/compras/1/estadisticas/

4. Ver resumen general:
   GET /api/compras/compras/resumen/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31

5. Ver compras de un proveedor:
   GET /api/compras/compras/por_proveedor/?proveedor=ABC

6. Filtrar compras por fecha:
   GET /api/compras/compras/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31

═══════════════════════════════════════════════════════════════════════════
PERMISOS POR ENDPOINT
═══════════════════════════════════════════════════════════════════════════

Almacenista:
  ✓ Listar compras
  ✓ Ver detalle de compra
  ✓ Crear compra
  ✓ Actualizar compra (solo proveedor)
  ✓ Ver detalles de compra

Supervisor/Admin:
  ✓ Todo lo anterior +
  ✓ Anular compra
  ✓ Eliminar compra
  ✓ Ver estadísticas
  ✓ Ver resumen general

═══════════════════════════════════════════════════════════════════════════
DIFERENCIAS CON VENTAS
═══════════════════════════════════════════════════════════════════════════

Compras:
  - Aumenta el inventario (ENTRADA)
  - Se registra con nombre de proveedor (string)
  - Se puede anular (reduce stock)
  - Margen potencial (vs precio de venta)

Ventas:
  - Reduce el inventario (SALIDA)
  - Se registra con cliente (ForeignKey)
  - Se puede cancelar (devuelve stock)
  - Estados: PENDIENTE, COMPLETADA, CANCELADA

═══════════════════════════════════════════════════════════════════════════
"""