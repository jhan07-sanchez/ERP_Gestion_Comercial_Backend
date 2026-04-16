# Move content from permissions.py here
from functools import wraps
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.exceptions import PermissionDenied
from apps.caja.services.caja_control import CajaControlService

class CajaAbiertaPermission(BasePermission):
    """
    Permission reutilizable que verifica que el usuario tiene
    una sesión de caja abierta antes de permitir operaciones de escritura.
    """
    message = "Debe abrir una caja antes de realizar operaciones."

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return CajaControlService.tiene_caja_abierta(request.user)

def requiere_caja_abierta(func):
    """
    Decorador que verifica que el usuario tiene caja abierta
    antes de ejecutar una función/vista.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        request = None
        for arg in args:
            if hasattr(arg, "user"):
                request = arg
                break
        if request is None:
            raise PermissionDenied("No se pudo determinar el usuario para verificar caja.")
        if not CajaControlService.tiene_caja_abierta(request.user):
            raise PermissionDenied("Debe abrir una caja antes de realizar operaciones.")
        return func(*args, **kwargs)
    return wrapper
