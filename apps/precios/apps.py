# apps/precio/apps.py
"""
¿Para qué sirve apps.py?
─────────────────────────
Django necesita "conocer" cada app. Este archivo:
1. Le dice a Django el nombre y configuración de la app.
2. En el método ready() podríamos conectar signals (como hace auditorias).

El campo default_auto_field define qué tipo de ID usa por defecto:
- BigAutoField → entero de 64 bits (puede llegar hasta 9,223,372,036,854,775,807)
  Esto es importante para un ERP que tendrá muchos registros.
"""

from django.apps import AppConfig


class PreciosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.precios"
    verbose_name = "Precios de Compra"
