from rest_framework.permissions import BasePermission


class PuedeVerReportes(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre__in=['Supervisor', 'Administrador']
        ).exists()


class PuedeVerReportesFinancieros(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre='Administrador'
        ).exists()
