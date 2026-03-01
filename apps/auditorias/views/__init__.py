# apps/auditorias/views/__init__.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                  VIEWS DE AUDITORÍA - Módulo __init__                      ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿POR QUÉ EXISTE ESTE ARCHIVO?
══════════════════════════════
Igual que en serializers/, este __init__.py convierte la carpeta
views/ en un paquete Python importable.

PATRÓN:
═══════
urls.py importa las views así:

    from apps.auditorias.views import LogAuditoriaViewSet
    from apps.auditorias.views import EstadisticasAuditoriaView

Este archivo hace posible esa importación limpia, aunque
el código real esté en views/api.py

FLUJO DE IMPORTACIÓN:
══════════════════════
  urls.py
    → importa desde apps.auditorias.views        (este __init__)
      → que re-exporta desde apps.auditorias.views.api

Autor: Sistema ERP
"""

from apps.auditorias.views.api import (
    LogAuditoriaViewSet,
    EstadisticasAuditoriaView,
)

# Control de exportaciones públicas
__all__ = [
    "LogAuditoriaViewSet",
    "EstadisticasAuditoriaView",
]
