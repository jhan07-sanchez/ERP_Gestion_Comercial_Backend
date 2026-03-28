import time
from django.conf import settings
from django.contrib.auth import logout
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class SessionTimeoutMiddleware(MiddlewareMixin):
    """
    Middleware de nivel empresarial para forzar el cierre de sesión
    tras un periodo de inactividad (1 hora por defecto).
    """

    def process_request(self, request):
        # Solo aplica a usuarios autenticados
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return

        current_time = int(time.time())

        # Intentar obtener el tiempo de inactividad configurable o usar SESSION_COOKIE_AGE
        timeout_seconds = getattr(settings, "SESSION_COOKIE_AGE", 3600)

        # Obtener la última actividad de la sesión
        last_activity = request.session.get("last_activity")

        if last_activity:
            elapsed_time = current_time - last_activity
            if elapsed_time > timeout_seconds:
                # El usuario superó el tiempo máximo de inactividad
                logger.info(
                    f"Sesión caducada por inactividad para el usuario: {request.user.email}"
                )
                logout(request)
                # Opcional: Agregar un mensaje en request forzando 401 si es API
                return

        # Si la sesión sigue activa, actualizar el timestamp
        request.session["last_activity"] = current_time
