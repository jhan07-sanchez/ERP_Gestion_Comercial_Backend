from rest_framework.permissions import BasePermission, SAFE_METHODS


class SoloLectura(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class SoloLecturaOCrear(BasePermission):
    def has_permission(self, request, view):
        return request.method in ['GET', 'POST', 'HEAD', 'OPTIONS']


class PuedeEliminar(BasePermission):
    message = "No tienes permiso para eliminar."

    def has_permission(self, request, view):
        if request.method != 'DELETE':
            return True

        return (
            request.user.is_authenticated and
            request.user.usuario_roles.filter(
                rol__nombre__in=['Supervisor', 'Administrador']
            ).exists()
        )


class PuedeGestionarVentas(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre__in=['Vendedor', 'Supervisor', 'Administrador']
        ).exists()


class PuedeGestionarCompras(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre__in=['Almacenista', 'Supervisor', 'Administrador']
        ).exists()


class PuedeGestionarInventario(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre__in=['Almacenista', 'Supervisor', 'Administrador']
        ).exists()


class PuedeGestionarCaja(BasePermission):
    def has_permission(self, request, view):
        return request.user.usuario_roles.filter(
            rol__nombre__in=['Cajero', 'Supervisor', 'Administrador']
        ).exists()
