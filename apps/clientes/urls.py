# apps/clientes/urls.py
"""
URLs para la app de Clientes

Este archivo define las rutas de la API para:
- Clientes

Estructura modular siguiendo el patrón de apps anteriores
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.clientes.views import ClienteViewSet

app_name = 'clientes'

# Crear router
router = DefaultRouter()

# Registrar ViewSets
router.register(r'', ClienteViewSet, basename='cliente')

# URLs
urlpatterns = [
    path('', include(router.urls)),
]

"""
═══════════════════════════════════════════════════════════════════════════
RUTAS GENERADAS AUTOMÁTICAMENTE POR EL ROUTER
═══════════════════════════════════════════════════════════════════════════

CLIENTES:
─────────
Básicas:
  GET    /api/clientes/                          - Listar clientes
  POST   /api/clientes/                          - Crear cliente
  GET    /api/clientes/{id}/                     - Ver detalle
  PUT    /api/clientes/{id}/                     - Actualizar completo
  PATCH  /api/clientes/{id}/                     - Actualizar parcial
  DELETE /api/clientes/{id}/                     - Eliminar

Acciones personalizadas:
  POST   /api/clientes/{id}/activar/             - Activar cliente
  POST   /api/clientes/{id}/desactivar/          - Desactivar cliente
  GET    /api/clientes/{id}/estadisticas/        - Estadísticas del cliente
  GET    /api/clientes/frecuentes/               - Clientes frecuentes
  GET    /api/clientes/mejores/                  - Mejores clientes
  GET    /api/clientes/inactivos/                - Clientes inactivos
  GET    /api/clientes/buscar/                   - Buscar clientes

Filtros disponibles:
  ?estado=true               - Filtrar por estado (true/false)
  ?nombre=Juan               - Filtrar por nombre
  ?documento=123456          - Filtrar por documento
  ?search=texto              - Búsqueda general (nombre, doc, email, tel)

═══════════════════════════════════════════════════════════════════════════
EJEMPLOS DE USO
═══════════════════════════════════════════════════════════════════════════

1. Crear un cliente:
   POST /api/clientes/
   {
     "nombre": "Juan Pérez García",
     "documento": "1234567890",
     "telefono": "3001234567",
     "email": "juan.perez@email.com",
     "direccion": "Calle 123 #45-67",
     "estado": true
   }

2. Actualizar cliente:
   PATCH /api/clientes/1/
   {
     "telefono": "3009876543",
     "email": "nuevo.email@email.com"
   }

3. Activar cliente:
   POST /api/clientes/1/activar/

4. Desactivar cliente:
   POST /api/clientes/1/desactivar/

5. Ver estadísticas de un cliente:
   GET /api/clientes/1/estadisticas/

6. Ver clientes frecuentes (top 10):
   GET /api/clientes/frecuentes/?limite=10

7. Ver mejores clientes por monto gastado:
   GET /api/clientes/mejores/?limite=5

8. Ver clientes inactivos (30 días sin comprar):
   GET /api/clientes/inactivos/?dias=30

9. Buscar clientes:
   GET /api/clientes/buscar/?q=Juan

10. Filtrar clientes activos:
    GET /api/clientes/?estado=true

═══════════════════════════════════════════════════════════════════════════
VALIDACIONES AUTOMÁTICAS
═══════════════════════════════════════════════════════════════════════════

Al crear/actualizar:
  ✓ Nombre: mínimo 3 caracteres
  ✓ Documento: único, solo números, mínimo 5 caracteres
  ✓ Email: formato válido, único (si se proporciona)
  ✓ Teléfono: solo números, 7-20 dígitos (si se proporciona)
  ✓ Documento: NO se puede modificar una vez creado

Al eliminar:
  ✓ No se puede eliminar si tiene ventas registradas
  ✓ Alternativa: desactivar el cliente

═══════════════════════════════════════════════════════════════════════════
PERMISOS POR ENDPOINT
═══════════════════════════════════════════════════════════════════════════

Vendedor:
  ✓ Listar clientes
  ✓ Ver detalle de cliente
  ✓ Crear cliente
  ✓ Actualizar cliente
  ✓ Buscar clientes

Supervisor/Admin:
  ✓ Todo lo anterior +
  ✓ Eliminar cliente
  ✓ Activar/Desactivar cliente
  ✓ Ver estadísticas de cliente
  ✓ Ver clientes frecuentes
  ✓ Ver mejores clientes
  ✓ Ver clientes inactivos

═══════════════════════════════════════════════════════════════════════════
RESPUESTAS TÍPICAS
═══════════════════════════════════════════════════════════════════════════

Crear cliente:
{
  "detail": "Cliente creado exitosamente",
  "cliente": {
    "id": 1,
    "nombre": "Juan Pérez García",
    "documento": "1234567890",
    "telefono": "3001234567",
    "email": "juan.perez@email.com",
    "direccion": "Calle 123 #45-67",
    "estado": true,
    "estado_badge": {
      "texto": "ACTIVO",
      "color": "green",
      "icono": "✓"
    },
    "total_ventas": 0,
    "total_comprado": 0,
    "ultima_compra": null
  }
}

Estadísticas de cliente:
{
  "cliente": {
    "id": 1,
    "nombre": "Juan Pérez García",
    "documento": "1234567890",
    "estado": "ACTIVO"
  },
  "ventas": {
    "total_ventas": 15,
    "ventas_completadas": 12,
    "ventas_pendientes": 2,
    "ventas_canceladas": 1
  },
  "financiero": {
    "total_comprado": 5420000.0,
    "promedio_compra": 451666.67,
    "ticket_minimo": 80000.0,
    "ticket_maximo": 1200000.0
  },
  "actividad": {
    "primera_compra": "2025-11-15T10:30:00Z",
    "ultima_compra": "2026-01-25T14:20:00Z",
    "dias_desde_ultima_compra": 4
  }
}

═══════════════════════════════════════════════════════════════════════════
"""