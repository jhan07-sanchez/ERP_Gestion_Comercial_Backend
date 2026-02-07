# apps/proveedores/urls.py
"""
URLs para la app de Proveedores

Este archivo define las rutas de la API para:
- Proveedores

Estructura modular siguiendo el patrón de apps anteriores
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.proveedores.views import ProveedorViewSet

app_name = 'proveedores'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'', ProveedorViewSet, basename='proveedor')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

PROVEEDORES:
────────────
Básicas:
  GET    /api/proveedores/                          - Listar proveedores
  POST   /api/proveedores/                          - Crear proveedor
  GET    /api/proveedores/{id}/                     - Ver detalle
  PUT    /api/proveedores/{id}/                     - Actualizar completo
  PATCH  /api/proveedores/{id}/                     - Actualizar parcial
  DELETE /api/proveedores/{id}/                     - Eliminar

Acciones personalizadas:
  POST   /api/proveedores/{id}/activar/             - Activar proveedor
  POST   /api/proveedores/{id}/desactivar/          - Desactivar proveedor
  GET    /api/proveedores/{id}/estadisticas/        - Estadísticas del proveedor
  GET    /api/proveedores/frecuentes/               - Proveedores frecuentes
  GET    /api/proveedores/mejores/                  - Mejores proveedores
  GET    /api/proveedores/inactivos/                - Proveedores inactivos
  GET    /api/proveedores/buscar/                   - Buscar proveedores

Filtros disponibles:
  ?activo=true               - Filtrar por estado (true/false)
  ?nombre=ABC                - Filtrar por nombre
  ?documento=123456          - Filtrar por documento
  ?search=texto              - Búsqueda general (nombre, doc, email, tel)

═══════════════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════════════

1. Crear un proveedor:
   POST /api/proveedores/
   {
     "nombre": "Distribuidora ABC S.A.S.",
     "documento": "900123456-7",
     "telefono": "6012345678",
     "email": "ventas@abc.com",
     "direccion": "Calle 123 #45-67, Bogotá",
     "activo": true
   }

2. Actualizar proveedor:
   PATCH /api/proveedores/1/
   {
     "telefono": "6019876543",
     "email": "nuevo@abc.com"
   }

3. Activar proveedor:
   POST /api/proveedores/1/activar/

4. Desactivar proveedor:
   POST /api/proveedores/1/desactivar/

5. Ver estadísticas de un proveedor:
   GET /api/proveedores/1/estadisticas/

6. Ver proveedores frecuentes (top 10):
   GET /api/proveedores/frecuentes/?limite=10

7. Ver mejores proveedores por monto comprado:
   GET /api/proveedores/mejores/?limite=5

8. Ver proveedores inactivos (30 días sin compras):
   GET /api/proveedores/inactivos/?dias=30

9. Buscar proveedores:
   GET /api/proveedores/buscar/?q=ABC

10. Filtrar proveedores activos:
    GET /api/proveedores/?activo=true

═══════════════════════════════════════════════════════════════════════════
VALIDACIONES AUTOMÁTICAS
═══════════════════════════════════════════════════════════════════════════

Al crear/actualizar:
  ✓ Nombre: mínimo 3 caracteres
  ✓ Documento: único, solo números y guiones, mínimo 5 caracteres
  ✓ Email: formato válido, único (si se proporciona)
  ✓ Teléfono: solo números, 7-30 dígitos (si se proporciona)
  ✓ Documento: NO se puede modificar una vez creado

Al eliminar:
  ✓ No se puede eliminar si tiene compras registradas
  ✓ Alternativa: desactivar el proveedor

═══════════════════════════════════════════════════════════════════════════
PERMISOS POR ENDPOINT
═══════════════════════════════════════════════════════════════════════════

Almacenista:
  ✓ Listar proveedores
  ✓ Ver detalle de proveedor
  ✓ Crear proveedor
  ✓ Actualizar proveedor
  ✓ Buscar proveedores

Supervisor/Admin:
  ✓ Todo lo anterior +
  ✓ Eliminar proveedor
  ✓ Activar/Desactivar proveedor
  ✓ Ver estadísticas de proveedor
  ✓ Ver proveedores frecuentes
  ✓ Ver mejores proveedores
  ✓ Ver proveedores inactivos

═══════════════════════════════════════════════════════════════════════════
RESPUESTAS TÍPICAS
═══════════════════════════════════════════════════════════════════════════

Crear proveedor:
{
  "detail": "Proveedor creado exitosamente",
  "proveedor": {
    "id": 1,
    "nombre": "Distribuidora ABC S.A.S.",
    "documento": "900123456-7",
    "telefono": "6012345678",
    "email": "ventas@abc.com",
    "direccion": "Calle 123 #45-67, Bogotá",
    "activo": true,
    "estado_badge": {
      "texto": "ACTIVO",
      "color": "green",
      "icono": "✓"
    },
    "total_compras": 0,
    "total_comprado": 0,
    "ultima_compra": null
  }
}

Estadísticas de proveedor:
{
  "proveedor": {
    "id": 1,
    "nombre": "Distribuidora ABC S.A.S.",
    "documento": "900123456-7",
    "estado": "ACTIVO"
  },
  "compras": {
    "total_compras": 15
  },
  "financiero": {
    "total_comprado": 45200000.0,
    "promedio_compra": 3013333.33,
    "compra_minima": 500000.0,
    "compra_maxima": 8500000.0
  },
  "actividad": {
    "primera_compra": "2025-11-15",
    "ultima_compra": "2026-01-25",
    "dias_desde_ultima_compra": 12
  }
}

═══════════════════════════════════════════════════════════════════════════
"""