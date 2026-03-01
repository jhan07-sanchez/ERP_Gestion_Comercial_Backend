# apps/auditorias/middleware.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MIDDLEWARE DE AUDITORÍA - ERP                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿QUÉ ES UN MIDDLEWARE EN DJANGO?
═════════════════════════════════
Un middleware es una capa de código que se ejecuta EN CADA REQUEST antes
de llegar a la vista y/o EN CADA RESPONSE antes de salir al cliente.

Flujo de un request en Django:
  Cliente → Middleware 1 → Middleware 2 → ... → View → DB
  Cliente ← Middleware 1 ← Middleware 2 ← ... ← View ← DB

Nosotros usamos esto para:
1. Capturar automáticamente accesos denegados (403)
2. Registrar errores del servidor (500)
3. Medir tiempos de respuesta
4. Detectar intentos de acceso sospechosos

NOTA: El middleware NO registra cada GET/POST normal
(eso llenaría la DB). Solo registra eventos de seguridad.
Para acciones de negocio (crear venta, etc.) se usa registrar_log()
directamente en cada view.

Autor: Sistema ERP
"""

import time
import logging

logger = logging.getLogger("auditorias")


class AuditoriaMiddleware:
    """
    Middleware que captura eventos de seguridad automáticamente.

    CÓMO FUNCIONA:
    ──────────────
    Django llama a __init__ una sola vez al arrancar el servidor.
    Django llama a __call__ en CADA request que llega.

    En __call__:
    1. Registramos el tiempo de inicio
    2. Dejamos que el request continúe: response = self.get_response(request)
    3. Analizamos la respuesta y registramos logs si es necesario
    """

    def __init__(self, get_response):
        """
        Se ejecuta UNA VEZ al arrancar Django.

        get_response es la siguiente capa del stack de middlewares
        (o la view si es el último middleware).
        """
        self.get_response = get_response

        # Endpoints que NUNCA queremos loguear (demasiado verbosos)
        self.endpoints_excluidos = [
            "/api/auditorias/",  # Para no crear logs de logs
            "/admin/jsi18n/",
            "/favicon.ico",
            "/static/",
            "/media/",
            "/health/",  # Health checks de deployment
        ]

        # Métodos HTTP que auditamos automáticamente por seguridad
        self.metodos_auditados = {"POST", "PUT", "PATCH", "DELETE"}

    def __call__(self, request):
        """
        Se ejecuta EN CADA REQUEST.

        Patrón:
            código antes del view
            response = self.get_response(request)  ← ejecuta el view
            código después del view
            return response
        """
        # Capturamos tiempo de inicio
        inicio = time.time()

        # ── ANTES del view ────────────────────────────────────────────────
        # (aquí podemos leer el request pero NO la response todavía)

        # ── EJECUTAMOS EL VIEW ────────────────────────────────────────────
        response = self.get_response(request)

        # ── DESPUÉS del view ──────────────────────────────────────────────
        duracion_ms = int((time.time() - inicio) * 1000)

        # Registramos solo eventos importantes
        try:
            self._procesar_response(request, response, duracion_ms)
        except Exception as e:
            # Nunca interrumpimos el request por un error de auditoría
            logger.error(f"Error en AuditoriaMiddleware: {e}")

        return response

    def _procesar_response(self, request, response, duracion_ms: int):
        """
        Analiza la respuesta y registra logs según el código HTTP.

        Códigos HTTP importantes:
        ─────────────────────────
        401 → No autenticado (token inválido/expirado)
        403 → Autenticado pero sin permisos
        404 → No encontrado
        500 → Error interno del servidor
        """
        # Verificar si este endpoint está excluido
        for excluido in self.endpoints_excluidos:
            if request.path.startswith(excluido):
                return

        status_code = response.status_code
        usuario = getattr(request, "user", None)

        # ── Acceso denegado (403) ─────────────────────────────────────────
        if status_code == 403:
            self._registrar_acceso_denegado(request, usuario, duracion_ms)

        # ── No autenticado (401) ──────────────────────────────────────────
        elif status_code == 401:
            self._registrar_no_autenticado(request, duracion_ms)

        # ── Error del servidor (5xx) ───────────────────────────────────────
        elif status_code >= 500:
            self._registrar_error_servidor(request, usuario, status_code, duracion_ms)

    def _registrar_acceso_denegado(self, request, usuario, duracion_ms):
        """Registra un intento de acceso sin permisos."""
        from apps.auditorias.utils import registrar_log, _obtener_ip

        nombre_usuario = "Anónimo"
        if (
            usuario
            and hasattr(usuario, "is_authenticated")
            and usuario.is_authenticated
        ):
            nombre_usuario = (
                getattr(usuario, "get_full_name", lambda: "")() or usuario.username
            )

        registrar_log(
            usuario=usuario
            if (usuario and getattr(usuario, "is_authenticated", False))
            else None,
            accion="ACCESO_DENEGADO",
            modulo="SISTEMA",
            descripcion=(
                f"Acceso denegado a {request.method} {request.path} "
                f"para usuario: {nombre_usuario}"
            ),
            nivel="WARNING",
            exitoso=False,
            request=request,
            duracion_ms=duracion_ms,
            extra={
                "status_code": 403,
                "metodo": request.method,
                "path": request.path,
            },
        )

    def _registrar_no_autenticado(self, request, duracion_ms):
        """Registra un intento de acceso sin autenticación."""
        from apps.auditorias.utils import registrar_log

        registrar_log(
            accion="ACCESO_DENEGADO",
            modulo="SISTEMA",
            descripcion=f"Acceso sin autenticación a {request.method} {request.path}",
            nivel="WARNING",
            exitoso=False,
            request=request,
            duracion_ms=duracion_ms,
            extra={
                "status_code": 401,
                "metodo": request.method,
                "path": request.path,
            },
        )

    def _registrar_error_servidor(self, request, usuario, status_code, duracion_ms):
        """Registra un error interno del servidor."""
        from apps.auditorias.utils import registrar_log

        registrar_log(
            usuario=usuario
            if (usuario and getattr(usuario, "is_authenticated", False))
            else None,
            accion="ERROR",
            modulo="SISTEMA",
            descripcion=f"Error {status_code} en {request.method} {request.path}",
            nivel="ERROR",
            exitoso=False,
            request=request,
            duracion_ms=duracion_ms,
            extra={
                "status_code": status_code,
                "metodo": request.method,
                "path": request.path,
            },
        )
