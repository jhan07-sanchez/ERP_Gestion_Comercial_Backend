# apps/auditorias/signals.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SIGNALS DE AUDITORÍA - ERP                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿QUÉ SON LOS SIGNALS EN DJANGO?
════════════════════════════════
Los signals son el patrón "Observer/Event" de Django.
Permiten que componentes desacoplados se "notifiquen" entre sí.

Django envía signals automáticamente en ciertos momentos:
  - user_logged_in     → cuando alguien hace login exitoso
  - user_logged_out    → cuando alguien hace logout
  - user_login_failed  → cuando falla el login

Nosotros nos "suscribimos" a esos eventos con @receiver
para capturarlos y registrar el log.

VENTAJA DEL ENFOQUE CON SIGNALS:
═════════════════════════════════
No necesitamos modificar las views de autenticación.
El log se registra automáticamente sin importar desde dónde
el usuario haga login (Admin, API, etc.)

Autor: Sistema ERP
"""

import logging
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

logger = logging.getLogger("auditorias")


@receiver(user_logged_in)
def log_login_exitoso(sender, request, user, **kwargs):
    """
    Se ejecuta automáticamente cuando un usuario inicia sesión exitosamente.

    PARÁMETROS que Django pasa al signal:
    ──────────────────────────────────────
    sender  → la clase que envió el signal
    request → el HttpRequest
    user    → la instancia del usuario que inició sesión
    kwargs  → argumentos adicionales (siempre incluir **kwargs)
    """
    try:
        from apps.auditorias.utils import registrar_log

        registrar_log(
            usuario=user,
            accion="LOGIN",
            modulo="USUARIOS",
            descripcion=f"Inicio de sesión exitoso: {user.get_full_name() or user.username}",
            nivel="INFO",
            exitoso=True,
            request=request,
            extra={
                "username": user.username,
                "email": getattr(user, "email", ""),
                "is_staff": user.is_staff,
            },
        )
    except Exception as e:
        logger.error(f"Error en signal login: {e}")


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    """
    Se ejecuta automáticamente cuando un usuario cierra sesión.
    """
    try:
        from apps.auditorias.utils import registrar_log

        registrar_log(
            usuario=user,
            accion="LOGOUT",
            modulo="USUARIOS",
            descripcion=f"Cierre de sesión: {user.get_full_name() or user.username if user else 'Desconocido'}",
            nivel="INFO",
            exitoso=True,
            request=request,
        )
    except Exception as e:
        logger.error(f"Error en signal logout: {e}")


@receiver(user_login_failed)
def log_login_fallido(sender, credentials, request, **kwargs):
    """
    Se ejecuta automáticamente cuando falla un intento de login.

    IMPORTANTE: credentials contiene el username que intentó,
    pero NO la contraseña (por seguridad Django no la pasa).
    """
    try:
        from apps.auditorias.utils import registrar_log, _obtener_ip

        username_intento = credentials.get("username", "desconocido")

        registrar_log(
            accion="LOGIN_FALLIDO",
            modulo="USUARIOS",
            descripcion=f'Intento de login fallido con usuario: "{username_intento}"',
            nivel="WARNING",
            exitoso=False,
            request=request,
            extra={
                "username_intento": username_intento,
                "ip": _obtener_ip(request) if request else None,
            },
        )
    except Exception as e:
        logger.error(f"Error en signal login_fallido: {e}")
