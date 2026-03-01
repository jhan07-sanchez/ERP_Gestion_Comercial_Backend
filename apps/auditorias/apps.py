# apps/auditorias/apps.py
"""
Configuración de la app Auditorias.

¿Por qué es importante apps.py?
────────────────────────────────
El método ready() se ejecuta cuando Django termina de cargar.
Es el lugar correcto para conectar signals.

Si no importamos los signals aquí, nunca se "escucharían"
los eventos de login/logout.
"""

from django.apps import AppConfig


class AuditoriasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.auditorias"
    verbose_name = "Auditorías"

    def ready(self):
        """
        Se ejecuta cuando Django termina de iniciar.
        Aquí conectamos los signals.
        """
        import apps.auditorias.signals  # noqa: F401 - Importar para registrar receivers
