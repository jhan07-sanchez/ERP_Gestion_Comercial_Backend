from rest_framework.permissions import BasePermission


class PermisosPersonalizadosPorAccion(BasePermission):
    """
    Clase base para permisos que dependen de la acción del ViewSet
    """

    def get_required_roles(self, action, method):
        return ['Administrador']

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        action = getattr(view, 'action', None)
        roles_requeridos = self.get_required_roles(action, request.method)

        return request.user.usuario_roles.filter(
            rol__nombre__in=roles_requeridos
        ).exists()
