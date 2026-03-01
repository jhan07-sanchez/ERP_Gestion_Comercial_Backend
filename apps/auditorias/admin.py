# apps/auditorias/admin.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ADMIN DE AUDITORÍA - ERP                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

Configura el panel de administración de Django para ver los logs.

¿Por qué tener admin si ya tenemos la API?
──────────────────────────────────────────
El admin de Django es útil para el equipo técnico/de soporte,
especialmente para investigar incidentes rápidamente sin necesidad
de ir al frontend.

Autor: Sistema ERP
"""

from django.contrib import admin
from django.utils.html import format_html
from apps.auditorias.models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    """
    Configuración del panel admin para LogAuditoria.

    Características:
    ────────────────
    - Solo lectura (no se pueden editar logs)
    - Filtros por módulo, acción, nivel, fecha
    - Búsqueda por texto
    - Colores según severidad
    """

    # Columnas en la lista
    list_display = [
        "fecha_hora",
        "icono_accion_display",
        "usuario_nombre",
        "modulo",
        "accion",
        "nivel_coloreado",
        "descripcion_corta",
        "ip_address",
        "exitoso_display",
    ]

    # Filtros en el panel lateral
    list_filter = [
        "modulo",
        "accion",
        "nivel",
        "exitoso",
        "metodo_http",
        ("fecha_hora", admin.DateFieldListFilter),
    ]

    # Búsqueda
    search_fields = [
        "usuario_nombre",
        "descripcion",
        "ip_address",
        "objeto_repr",
        "endpoint",
    ]

    # Orden por defecto
    ordering = ["-fecha_hora"]

    # Paginación
    list_per_page = 50

    # Campos de solo lectura
    #readonly_fields = "__all__"

    def has_add_permission(self, request):
        """No permitir crear logs manualmente desde el admin."""
        return False

    def has_change_permission(self, request, obj=None):
        """No permitir editar logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Solo superusuarios pueden eliminar logs."""
        return request.user.is_superuser

    def icono_accion_display(self, obj):
        """Muestra el emoji de la acción."""
        return obj.icono_accion

    icono_accion_display.short_description = ""

    def nivel_coloreado(self, obj):
        """Muestra el nivel con color HTML."""
        colores = {
            "INFO": "#28a745",
            "WARNING": "#ffc107",
            "ERROR": "#dc3545",
            "CRITICAL": "#721c24",
        }
        color = colores.get(obj.nivel, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_nivel_display(),
        )

    nivel_coloreado.short_description = "Nivel"

    def descripcion_corta(self, obj):
        """Muestra los primeros 80 caracteres de la descripción."""
        if len(obj.descripcion) > 80:
            return obj.descripcion[:80] + "..."
        return obj.descripcion

    descripcion_corta.short_description = "Descripción"

    def exitoso_display(self, obj):
        """Muestra ✅ o ❌ según si fue exitoso."""
        return "✅" if obj.exitoso else "❌"

    exitoso_display.short_description = "OK"

    #def get_readonly_fields(self, request, obj=None):
        #"""Todos los campos son de solo lectura."""
        #if obj:
           # return [f.name for f in obj._meta.fields]
        #return []
