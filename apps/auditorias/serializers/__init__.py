# apps/auditorias/serializers/__init__.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               SERIALIZERS DE AUDITORÍA - Módulo __init__                   ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿POR QUÉ EXISTE ESTE ARCHIVO?
══════════════════════════════
En Python, una CARPETA se convierte en un "paquete" (módulo importable)
cuando tiene un archivo __init__.py dentro.

Sin este archivo:
    from apps.auditorias.serializers import LogAuditoriaListSerializer
    → ERROR: No module named 'apps.auditorias.serializers'

Con este archivo:
    from apps.auditorias.serializers import LogAuditoriaListSerializer
    → ✅ Funciona perfectamente

PATRÓN DE IMPORTACIÓN:
══════════════════════
Aquí re-exportamos todo lo que está en serializers.py
para que cualquier archivo del proyecto pueda importar así:

    from apps.auditorias.serializers import LogAuditoriaListSerializer
    from apps.auditorias.serializers import LogAuditoriaDetailSerializer
    from apps.auditorias.serializers import EstadisticasAuditoriaSerializer

En lugar de tener que escribir:
    from apps.auditorias.serializers.serializers import LogAuditoriaListSerializer

Autor: Sistema ERP
"""

from apps.auditorias.serializers.serializers import (
    LogAuditoriaListSerializer,
    LogAuditoriaDetailSerializer,
    EstadisticasAuditoriaSerializer,
)

# Definimos __all__ para controlar qué se exporta cuando alguien hace:
# from apps.auditorias.serializers import *
__all__ = [
    "LogAuditoriaListSerializer",
    "LogAuditoriaDetailSerializer",
    "EstadisticasAuditoriaSerializer",
]
