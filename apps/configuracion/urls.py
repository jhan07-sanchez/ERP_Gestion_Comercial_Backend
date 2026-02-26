# apps/configuracion/urls.py
"""
URLs para la app de Configuración

¿Por qué no usamos Router aquí?
---------------------------------
El Router de DRF es ideal para ModelViewSet (muchos registros, CRUD completo).
Aquí solo tenemos UN registro y endpoints específicos, así que usamos
path() directamente para mayor claridad y control.

Endpoints:
    GET    /api/configuracion/                     → Ver configuración
    PUT    /api/configuracion/                     → Actualización completa (solo Admin)
    PATCH  /api/configuracion/                     → Actualización parcial (solo Admin)
    POST   /api/configuracion/reset-consecutivo/   → Resetear consecutivo (solo Admin)
    GET    /api/configuracion/empresa/             → Info resumida de empresa

Autor: Sistema ERP
"""

from django.urls import path
from apps.configuracion.views import (
    ConfiguracionView,
    ResetConsecutivoView,
    InfoEmpresaView,
)

app_name = "configuracion"

urlpatterns = [
    # ── Configuración principal ────────────────────────────────────────────────
    path(
        "",
        ConfiguracionView.as_view(),
        name="configuracion",
    ),
    # ── Acción: Reset de consecutivo ──────────────────────────────────────────
    path(
        "reset-consecutivo/",
        ResetConsecutivoView.as_view(),
        name="reset-consecutivo",
    ),
    # ── Info pública de la empresa ────────────────────────────────────────────
    path(
        "empresa/",
        InfoEmpresaView.as_view(),
        name="info-empresa",
    ),
]

"""
═══════════════════════════════════════════════════════════════════════════
TABLA DE ENDPOINTS
═══════════════════════════════════════════════════════════════════════════

Método   URL                                    Rol requerido   Descripción
───────  ─────────────────────────────────────  ──────────────  ─────────────────────────────────
GET      /api/configuracion/                    Autenticado     Ver toda la configuración
PUT      /api/configuracion/                    Admin           Actualizar configuración completa
PATCH    /api/configuracion/                    Admin           Actualizar campos específicos
POST     /api/configuracion/reset-consecutivo/  Admin           Resetear consecutivo de documentos
GET      /api/configuracion/empresa/            Autenticado     Info básica de la empresa
═══════════════════════════════════════════════════════════════════════════
"""
