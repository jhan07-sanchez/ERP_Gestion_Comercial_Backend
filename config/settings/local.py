# config/settings/local.py
"""
Configuraciones para DESARROLLO LOCAL

Este archivo se usa cuando trabajas en tu máquina local.
Incluye herramientas de debug y configuraciones más permisivas.
"""

from .base import *
from .database import *
from .rest_framework import *
from .cors import *

# Debug
# =====

DEBUG = True

ALLOWED_HOSTS = ['*']


# Installed Apps para desarrollo
# ===============================

INSTALLED_APPS += [
    # Herramientas de desarrollo (descomentar si las instalas)
    # 'debug_toolbar',
    # 'django_extensions',
]


# Middleware para desarrollo
# ===========================

MIDDLEWARE += [
    # Debug Toolbar (descomentar si lo instalas)
    # 'debug_toolbar.middleware.DebugToolbarMiddleware',
]


# Debug Toolbar Configuration
# ============================

INTERNAL_IPS = [
    '127.0.0.1',
    'localhost',
]

# DEBUG_TOOLBAR_CONFIG = {
#     'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
# }


# Email Configuration (Desarrollo)
# =================================

# En desarrollo, los emails se muestran en consola
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# Logging Configuration
# =====================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'debug.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}


# REST Framework para desarrollo
# ===============================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',  # API navegable
)


# Cache (Desarrollo - Dummy Cache)
# =================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


# Performance
# ===========

# En desarrollo puedes desactivar algunas optimizaciones
# para facilitar el debugging

# Deshabilitar template caching
TEMPLATES[0]['OPTIONS']['debug'] = True

# Mostrar SQL queries en consola
# LOGGING['loggers']['django.db.backends']['level'] = 'DEBUG'


# Archivos estáticos en desarrollo
# =================================

# Django sirve archivos estáticos automáticamente en desarrollo
# No necesitas configuración adicional


# CORS más permisivo en desarrollo
# =================================

CORS_ALLOW_ALL_ORIGINS = True  # Permitir todos los orígenes en desarrollo


# Security (Relajado en desarrollo)
# ==================================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False


# Crear carpeta de logs si no existe
# ===================================

import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)


print(" Servidor corriendo en modo DESARROLLO")
print(f" BASE_DIR: {BASE_DIR}")
print(f"  Database: {DATABASES['default']['NAME']}")
print(f" Debug: {DEBUG}")