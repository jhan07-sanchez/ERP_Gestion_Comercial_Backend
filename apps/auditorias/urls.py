# apps/auditorias/urls.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    URLs DE AUDITORÍA - ERP                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝

Ruta base: /api/auditorias/

ENDPOINTS:
══════════════════════════════════════════════════════════

  LOGS
  GET  /api/auditorias/logs/                      → Listar todos los logs
  GET  /api/auditorias/logs/{id}/                 → Ver un log en detalle
  GET  /api/auditorias/logs/mis-logs/             → Mis propios logs
  GET  /api/auditorias/logs/por-objeto/           → Logs de un objeto (admin)
  GET  /api/auditorias/logs/actividad-usuario/    → Actividad de usuario (admin)

  ESTADÍSTICAS (solo admin)
  GET  /api/auditorias/estadisticas/              → KPIs del sistema de auditoría

FILTROS para /logs/:
  ?modulo=VENTAS
  ?accion=CREAR
  ?nivel=ERROR
  ?exitoso=false
  ?usuario=5
  ?fecha_inicio=2026-01-01
  ?fecha_fin=2026-01-31
  ?search=texto
  ?ordering=-fecha_hora

══════════════════════════════════════════════════════════
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.auditorias.views import (
    LogAuditoriaViewSet,
    EstadisticasAuditoriaView,
)

app_name = "auditorias"

router = DefaultRouter()
router.register(r"logs", LogAuditoriaViewSet, basename="log")

urlpatterns = [
    path("", include(router.urls)),
    path("estadisticas/", EstadisticasAuditoriaView.as_view(), name="estadisticas"),
]
