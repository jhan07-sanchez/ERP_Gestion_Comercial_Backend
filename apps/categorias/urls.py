# apps/categorias/urls.py
"""
URLs para la app de Categorías

Estructura modular siguiendo el patrón de arquitectura por dominio.
"""

from rest_framework.routers import DefaultRouter
from apps.categorias.views import CategoriaViewSet

app_name = 'categorias'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'', CategoriaViewSet, basename='categoria')

# URLs
urlpatterns = router.urls

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

CATEGORÍAS:
───────────
Básicas:
  GET    /api/categorias/                   - Listar categorías
  POST   /api/categorias/                   - Crear categoría
  GET    /api/categorias/{id}/              - Ver detalle
  PUT    /api/categorias/{id}/              - Actualizar completo
  PATCH  /api/categorias/{id}/              - Actualizar parcial
  DELETE /api/categorias/{id}/              - Eliminar

Acciones personalizadas:
  GET    /api/categorias/{id}/productos/    - Productos de la categoría
  GET    /api/categorias/{id}/estadisticas/ - Estadísticas de la categoría

Filtros disponibles:
  ?nombre=Electrónica      - Filtrar por nombre
  ?search=electro          - Búsqueda general (nombre, descripción)

═══════════════════════════════════════════════════════════════════════════
"""
