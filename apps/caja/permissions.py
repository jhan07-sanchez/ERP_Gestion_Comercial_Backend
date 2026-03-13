# apps/caja/permissions.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║            PERMISOS REUTILIZABLES - MÓDULO CAJA                            ║
║                                                                              ║
║  CajaAbiertaPermission:                                                     ║
║    Permission de DRF que verifica si el usuario tiene caja abierta.          ║
║    Aplicable a cualquier ViewSet que requiera operación financiera.          ║
║                                                                              ║
║  Uso:                                                                        ║
║    permission_classes = [IsAuthenticated, CajaAbiertaPermission]             ║
║                                                                              ║
║  Decorador:                                                                  ║
║    @requiere_caja_abierta                                                    ║
║    def mi_vista(request): ...                                                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from functools import wraps

from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied

from apps.caja.services.caja_control import CajaControlService


# ============================================================================
# PERMISSION DE DRF
# ============================================================================


class CajaAbiertaPermission(BasePermission):
    """
    Permission reutilizable que verifica que el usuario tiene
    una sesión de caja abierta antes de permitir operaciones de escritura.

    Comportamiento:
    - GET, HEAD, OPTIONS → permitido siempre (lectura)
    - POST, PUT, PATCH, DELETE → requiere caja abierta

    Uso en ViewSets:
        class VentaViewSet(viewsets.ModelViewSet):
            def get_permissions(self):
                if self.action in ["create", "completar", "registrar_pago"]:
                    return [IsAuthenticated(), CajaAbiertaPermission()]
                return [IsAuthenticated()]

    O directamente:
        permission_classes = [IsAuthenticated, CajaAbiertaPermission]
    """

    message = "Debe abrir una caja antes de realizar operaciones."

    def has_permission(self, request, view):
        # Operaciones de lectura siempre permitidas
        if request.method in SAFE_METHODS:
            return True

        # Verificar que el usuario tenga caja abierta
        if not request.user or not request.user.is_authenticated:
            return False

        return CajaControlService.tiene_caja_abierta(request.user)


# ============================================================================
# DECORADOR REUTILIZABLE
# ============================================================================


def requiere_caja_abierta(func):
    """
    Decorador que verifica que el usuario tiene caja abierta
    antes de ejecutar una función/vista.

    Uso en vistas DRF:
        @action(detail=True, methods=["post"])
        @requiere_caja_abierta
        def registrar_pago(self, request, pk=None):
            ...

    Uso en funciones de servicio:
        @requiere_caja_abierta
        def procesar_pago(request, venta_id):
            ...

    Lanza PermissionDenied si no hay caja abierta
    (DRF lo convierte automáticamente en HTTP 403).
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extraer request — puede ser primer arg (función) o segundo (método de clase)
        request = None
        for arg in args:
            if hasattr(arg, "user"):
                request = arg
                break

        if request is None:
            raise PermissionDenied(
                "No se pudo determinar el usuario para verificar caja."
            )

        if not CajaControlService.tiene_caja_abierta(request.user):
            raise PermissionDenied(
                "Debe abrir una caja antes de realizar operaciones."
            )

        return func(*args, **kwargs)

    return wrapper
