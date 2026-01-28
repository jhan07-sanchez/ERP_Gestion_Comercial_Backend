from rest_framework.permissions import BasePermission, SAFE_METHODS
from django.utils import timezone


class PuedeEditarPropio(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if request.user.usuario_roles.filter(rol__nombre='Administrador').exists():
            return True

        return hasattr(obj, 'usuario') and obj.usuario == request.user


class PuedeVerPropio(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.usuario_roles.filter(
            rol__nombre__in=['Supervisor', 'Administrador']
        ).exists():
            return True

        return hasattr(obj, 'usuario') and obj.usuario == request.user


class PuedeCancelarVenta(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.usuario_roles.filter(
            rol__nombre__in=['Supervisor', 'Administrador']
        ).exists():
            return True

        if request.user.usuario_roles.filter(rol__nombre='Vendedor').exists():
            return obj.usuario == request.user and obj.fecha.date() == timezone.now().date()

        return False
