# apps/productos/urls.py
"""
URLs para la app de Productos

Estructura modular siguiendo el patrón de arquitectura por dominio.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.productos.views import ProductoViewSet

app_name = 'productos'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'productos', ProductoViewSet, basename='producto')

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
  GET    /api/productos/                    - Listar productos
  POST   /api/productos/                    - Crear producto
  GET    /api/productos/{id}/               - Ver detalle
  PUT    /api/productos/{id}/               - Actualizar completo
  PATCH  /api/productos/{id}/               - Actualizar parcial
  DELETE /api/productos/{id}/               - Eliminar

Acciones personalizadas:
  GET    /api/productos/stock_bajo/         - Productos con stock bajo
  POST   /api/productos/{id}/activar/       - Activar producto
  POST   /api/productos/{id}/desactivar/    - Desactivar producto
  GET    /api/productos/{id}/movimientos/   - Historial de movimientos
  GET    /api/productos/{id}/estadisticas/  - Estadísticas del producto
  POST   /api/productos/{id}/ajustar_stock/ - Ajustar stock manualmente
  GET    /api/productos/siguiente_codigo/   - Siguiente código disponible

Filtros disponibles:
  ?categoria_id=1          - Filtrar por ID de categoría
  ?categoria=Electrónica   - Filtrar por nombre de categoría
  ?estado=true             - Filtrar por estado (activo/inactivo)
  ?precio_min=1000         - Precio mínimo
  ?precio_max=50000        - Precio máximo
  ?search=laptop           - Búsqueda general (código, nombre, descripción)

═══════════════════════════════════════════════════════════════════════════
"""
