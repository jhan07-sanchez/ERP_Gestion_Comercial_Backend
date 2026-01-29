# apps/ventas/urls.py
"""
URLs para la app de Ventas

Este archivo define las rutas de la API para:
- Ventas
- Detalles de Venta

Estructura modular siguiendo el patrón de apps/usuarios y apps/inventario
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.ventas.views import VentaViewSet, DetalleVentaViewSet

app_name = 'ventas'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'ventas', VentaViewSet, basename='venta')
router.register(r'detalles', DetalleVentaViewSet, basename='detalle')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

VENTAS:
──────
Básicas:
  GET    /api/ventas/ventas/                    - Listar ventas
  POST   /api/ventas/ventas/                    - Crear venta
  GET    /api/ventas/ventas/{id}/               - Ver detalle
  PUT    /api/ventas/ventas/{id}/               - Actualizar completo
  PATCH  /api/ventas/ventas/{id}/               - Actualizar parcial
  DELETE /api/ventas/ventas/{id}/               - Eliminar

Acciones personalizadas:
  POST   /api/ventas/ventas/{id}/completar/     - Completar venta
  POST   /api/ventas/ventas/{id}/cancelar/      - Cancelar venta
  GET    /api/ventas/ventas/{id}/estadisticas/  - Estadísticas de la venta
  GET    /api/ventas/ventas/resumen/            - Resumen general
  GET    /api/ventas/ventas/pendientes/         - Ventas pendientes
  GET    /api/ventas/ventas/completadas/        - Ventas completadas

Filtros disponibles:
  ?cliente_id=1              - Filtrar por ID de cliente
  ?cliente=Juan              - Filtrar por nombre de cliente
  ?estado=COMPLETADA         - Filtrar por estado (PENDIENTE/COMPLETADA/CANCELADA)
  ?usuario_id=1              - Filtrar por ID de usuario
  ?fecha_inicio=2026-01-01   - Fecha inicial
  ?fecha_fin=2026-01-31      - Fecha final
  ?total_min=100000          - Total mínimo
  ?total_max=500000          - Total máximo
  ?search=12345              - Búsqueda general (cliente, documento, ID)

DETALLES DE VENTA:
──────────────────
Básicas (Solo lectura):
  GET    /api/ventas/detalles/                  - Listar detalles
  GET    /api/ventas/detalles/{id}/             - Ver detalle

Filtros disponibles:
  ?venta_id=1                - Filtrar por ID de venta
  ?producto_id=1             - Filtrar por ID de producto

═══════════════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════════════

1. Crear una venta:
   POST /api/ventas/ventas/
   {
     "cliente_id": 1,
     "estado": "PENDIENTE",
     "detalles": [
       {
         "producto_id": 1,
         "cantidad": 2,
         "precio_unitario": 2000000
       },
       {
         "producto_id": 2,
         "cantidad": 1,
         "precio_unitario": 80000
       }
     ]
   }

2. Completar una venta:
   POST /api/ventas/ventas/1/completar/
   {
     "notas": "Entrega realizada"
   }

3. Cancelar una venta:
   POST /api/ventas/ventas/1/cancelar/
   {
     "motivo": "Cliente canceló el pedido"
   }

4. Ver ventas pendientes:
   GET /api/ventas/ventas/pendientes/

5. Ver resumen de ventas:
   GET /api/ventas/ventas/resumen/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31

6. Ver estadísticas de una venta:
   GET /api/ventas/ventas/1/estadisticas/

7. Filtrar ventas por cliente y estado:
   GET /api/ventas/ventas/?cliente_id=1&estado=COMPLETADA

═══════════════════════════════════════════════════════════════════════════
PERMISOS POR ENDPOINT
═══════════════════════════════════════════════════════════════════════════

Vendedor:
  ✓ Listar ventas
  ✓ Ver detalle de venta
  ✓ Crear venta
  ✓ Completar venta
  ✓ Ver detalles de venta

Supervisor/Admin:
  ✓ Todo lo anterior +
  ✓ Cancelar venta
  ✓ Eliminar venta
  ✓ Ver estadísticas
  ✓ Ver resumen general

═══════════════════════════════════════════════════════════════════════════
"""