# config/settings/test.py
"""
Configuraciones para TESTING

Este archivo se usa cuando ejecutas los tests.
Optimizado para velocidad y aislamiento.
"""

from .base import *
from .rest_framework import *

# Debug
# =====

DEBUG = False


# Database (Testing - SQLite en memoria)
# =======================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'ATOMIC_REQUESTS': True,
    }
}


# Password Hashers (Testing - Más rápido)
# ========================================

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]


# Email (Testing - En memoria)
# =============================

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'


# Cache (Testing - Dummy)
# ========================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}


# Media files (Testing - Temporal)
# =================================

import tempfile

MEDIA_ROOT = tempfile.mkdtemp()


# Logging (Testing - Mínimo)
# ===========================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}


# REST Framework (Testing)
# =========================

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
)

# Sin throttling en tests
REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'] = []
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {}


# CORS (Testing - Permisivo)
# ===========================

CORS_ALLOW_ALL_ORIGINS = True


# Security (Relajado para tests)
# ===============================

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False


# Celery (Testing - Sincrónico)
# ==============================

# Si usas Celery, ejecutar tareas sincrónicamente en tests
# CELERY_TASK_ALWAYS_EAGER = True
# CELERY_TASK_EAGER_PROPAGATES = True


print("🧪 Ejecutando TESTS")