from rest_framework.permissions import BasePermission


class EsAdministrador(BasePermission):
    message = "Solo los administradores pueden realizar esta acción."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(rol__nombre='Administrador').exists()
        )


class EsSupervisor(BasePermission):
    message = "Necesitas ser supervisor o administrador."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(
                rol__nombre__in=['Supervisor', 'Administrador']
            ).exists()
        )


class EsVendedor(BasePermission):
    message = "Necesitas ser vendedor o superior."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(
                rol__nombre__in=['Vendedor', 'Supervisor', 'Administrador']
            ).exists()
        )


class EsCajero(BasePermission):
    message = "Necesitas ser cajero o superior."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(
                rol__nombre__in=['Cajero', 'Supervisor', 'Administrador']
            ).exists()
        )


class EsAlmacenista(BasePermission):
    message = "Necesitas ser almacenista o superior."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(
                rol__nombre__in=['Almacenista', 'Supervisor', 'Administrador']
            ).exists()
        )

