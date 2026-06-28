# apps/usuarios/apps.py
from django.apps import AppConfig

class ConfiguracionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.configuracion'
    verbose_name = 'Configuración'

    def ready(self):
        import sys
        if 'runserver' in sys.argv:
            try:
                from .models import CondicionPago
                if CondicionPago.objects.count() == 0:
                    CondicionPago.objects.create(nombre="CONTADO", dias_plazo=0, es_contado=True)
                    CondicionPago.objects.create(nombre="CRÉDITO 15 DÍAS", dias_plazo=15, es_contado=False)
                    CondicionPago.objects.create(nombre="CRÉDITO 30 DÍAS", dias_plazo=30, es_contado=False)
            except Exception:
                pass