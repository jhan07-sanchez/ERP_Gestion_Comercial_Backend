# config/settings/__init__.py
"""
Configuraciones de Django divididas por entorno

Este archivo carga la configuración adecuada según la variable
de entorno DJANGO_SETTINGS_MODULE o DJANGO_ENV.

Uso:
    # En desarrollo (por defecto)
    export DJANGO_ENV=local
    python manage.py runserver

    # En producción
    export DJANGO_ENV=production
    python manage.py runserver

    # En testing
    export DJANGO_ENV=test
    python manage.py test

    # O directamente con DJANGO_SETTINGS_MODULE
    export DJANGO_SETTINGS_MODULE=config.settings.local
"""

import os

# Detectar el entorno
DJANGO_ENV = os.getenv('DJANGO_ENV', 'local')

# Cargar la configuración apropiada
if DJANGO_ENV == 'production':
    from .production import *
    print("✅ Usando configuración de PRODUCCIÓN")
elif DJANGO_ENV == 'test':
    from .test import *
    print("✅ Usando configuración de TESTING")
else:
    from .local import *
    print("✅ Usando configuración de DESARROLLO (local)")