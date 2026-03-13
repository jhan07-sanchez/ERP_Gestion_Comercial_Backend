# apps/caja/apps.py
from django.apps import AppConfig


class CajaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.caja'
    verbose_name = 'Caja'

    def ready(self):
        import apps.caja.signals  # noqa: F401