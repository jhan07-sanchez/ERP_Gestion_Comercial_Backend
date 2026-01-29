# config/settings/cors.py
"""
Configuraciones de CORS (Cross-Origin Resource Sharing)

Este archivo contiene las configuraciones para permitir peticiones
desde otros dominios (frontend en React, Vue, Angular, etc.)
"""

import os

# CORS Configuration
# ==================

# Origenes permitidos
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",      # React
    "http://localhost:8080",      # Vue
    "http://localhost:4200",      # Angular
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:4200",
]

# Si quieres permitir todos los orígenes (solo desarrollo)
# CORS_ALLOW_ALL_ORIGINS = True

# Permitir credenciales (cookies, authorization headers)
CORS_ALLOW_CREDENTIALS = True

# Headers permitidos
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Métodos HTTP permitidos
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

# Headers expuestos al frontend
CORS_EXPOSE_HEADERS = [
    'Content-Type',
    'X-CSRFToken',
]

# Tiempo de cache para preflight requests
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 horas


# CSRF Configuration
# ==================

# Trusted origins para CSRF
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]

# Cookie settings
CSRF_COOKIE_HTTPONLY = False
CSRF_COOKIE_SECURE = False  # True en producción con HTTPS
CSRF_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # True en producción con HTTPS
SESSION_COOKIE_SAMESITE = 'Lax'