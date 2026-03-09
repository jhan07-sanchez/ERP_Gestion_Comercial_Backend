# apps/caja/urls.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        URLs - MÓDULO CAJA                                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Ruta base: /api/caja/

═══════════════════════════════════════════════════════════════════════════════
MÉTODOS DE PAGO
═══════════════════════════════════════════════════════════════════════════════
GET    /api/caja/metodos-pago/                  - Listar métodos
POST   /api/caja/metodos-pago/                  - Crear método (Admin)
GET    /api/caja/metodos-pago/{id}/             - Ver detalle
PATCH  /api/caja/metodos-pago/{id}/             - Actualizar (Admin)
POST   /api/caja/metodos-pago/{id}/activar/     - Activar (Admin)
POST   /api/caja/metodos-pago/{id}/desactivar/  - Desactivar (Admin)

═══════════════════════════════════════════════════════════════════════════════
CAJAS
═══════════════════════════════════════════════════════════════════════════════
GET    /api/caja/cajas/                         - Listar cajas
POST   /api/caja/cajas/                         - Crear caja (Admin)
GET    /api/caja/cajas/{id}/                    - Ver detalle
PATCH  /api/caja/cajas/{id}/                    - Actualizar (Admin)

═══════════════════════════════════════════════════════════════════════════════
SESIONES DE CAJA
═══════════════════════════════════════════════════════════════════════════════
GET    /api/caja/sesiones/                      - Listar sesiones
GET    /api/caja/sesiones/{id}/                 - Ver detalle completo
GET    /api/caja/sesiones/mi-sesion/            - Sesión activa del usuario
POST   /api/caja/sesiones/abrir/                - Abrir nueva sesión ←── CLAVE
POST   /api/caja/sesiones/{id}/cerrar/          - Cerrar sesión ←── CLAVE
POST   /api/caja/sesiones/{id}/movimiento/      - Registrar movimiento manual
POST   /api/caja/sesiones/{id}/arqueo/          - Realizar arqueo
GET    /api/caja/sesiones/{id}/resumen/         - Resumen de la sesión
GET    /api/caja/sesiones/resumen-hoy/          - Resumen del día (Supervisor)
GET    /api/caja/sesiones/resumen-rango/        - Resumen por rango (Supervisor)
        ?fecha_inicio=2026-01-01&fecha_fin=2026-01-31

═══════════════════════════════════════════════════════════════════════════════
MOVIMIENTOS (Solo lectura)
═══════════════════════════════════════════════════════════════════════════════
GET    /api/caja/movimientos/                   - Listar movimientos
GET    /api/caja/movimientos/{id}/              - Ver detalle

Filtros disponibles:
  ?sesion_id=1                - Filtrar por sesión
  ?tipo=EGRESO_GASTO          - Filtrar por tipo
  ?metodo_pago=1              - Filtrar por método de pago
  ?fecha_inicio=2026-01-01    - Fecha inicial
  ?fecha_fin=2026-01-31       - Fecha final
  ?search=descripcion         - Búsqueda en descripción

═══════════════════════════════════════════════════════════════════════════════
EJEMPLOS DE USO — Flujo completo de cajero
═══════════════════════════════════════════════════════════════════════════════

1. Al iniciar turno → verificar si tiene caja abierta:
   GET /api/caja/sesiones/mi-sesion/

2. Si no tiene → abrir caja:
   POST /api/caja/sesiones/abrir/
   {"caja_id": 1, "monto_inicial": 50000}

3. Registrar ingreso de venta (lo hace ventas automáticamente):
   (integración interna, no requiere llamada manual)

4. Registrar gasto manual:
   POST /api/caja/sesiones/5/movimiento/
   {"tipo": "EGRESO_GASTO", "monto": 8000, "descripcion": "Mensajería", "metodo_pago_id": 1}

5. Realizar arqueo de mitad de turno:
   POST /api/caja/sesiones/5/arqueo/
   {"monto_contado": 115000, "observaciones": "Todo cuadra"}

6. Ver resumen antes de cerrar:
   GET /api/caja/sesiones/5/resumen/

7. Cerrar caja:
   POST /api/caja/sesiones/5/cerrar/
   {"monto_contado": 178500, "detalle_billetes": {"100000": 1, "50000": 1, "20000": 1, "5000": 1, "1000": 3, "500": 1}}
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.caja.views import (
    MetodoPagoViewSet,
    CajaViewSet,
    SesionCajaViewSet,
    MovimientoCajaViewSet,
)

app_name = "caja"

router = DefaultRouter()
router.register(r"metodos-pago", MetodoPagoViewSet, basename="metodo-pago")
router.register(r"cajas", CajaViewSet, basename="caja")
router.register(r"sesiones", SesionCajaViewSet, basename="sesion")
router.register(r"movimientos", MovimientoCajaViewSet, basename="movimiento")

urlpatterns = [
    path("", include(router.urls)),
]
