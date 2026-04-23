from functools import wraps
from django.http import JsonResponse
from rest_framework import permissions

def usuario_tiene_modulo(usuario, codigo_modulo):
    """
    Verifica si el usuario tiene acceso a un módulo específico.
    Se requiere que la suscripción esté activa y que el plan incluya el módulo.
    """
    if not usuario.is_authenticated:
        return False

    # Validar si tiene empresa y suscripción
    if not hasattr(usuario, 'empresa') or not usuario.empresa:
        return False
    
    if not hasattr(usuario.empresa, 'suscripcion') or not usuario.empresa.suscripcion:
        return False

    suscripcion = usuario.empresa.suscripcion

    # Si la suscripción no está activa o el pago no está activo/en gracia
    if not suscripcion.esta_activa():
        return False

    if suscripcion.estado_pago not in ['activa', 'en_gracia']:
        return False

    # Verificar si el plan tiene el módulo asociado
    return suscripcion.plan.modulos.filter(codigo=codigo_modulo, activo=True).exists()


def requiere_modulo(codigo_modulo):
    """
    Decorador para vistas basadas en funciones.
    Bloquea el acceso si el usuario no tiene el módulo requerido en su plan.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not usuario_tiene_modulo(request.user, codigo_modulo):
                return JsonResponse(
                    {"error": f"Tu plan actual no incluye acceso al módulo: {codigo_modulo}"},
                    status=403
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


class RequireModuloPermission(permissions.BasePermission):
    """
    Permiso de Django REST Framework para proteger ViewSets o APIs.
    Uso: 
        permission_classes = [IsAuthenticated, RequireModuloPermission]
        modulo_requerido = 'ventas' # Atributo en el ViewSet
    """
    message = "Tu plan actual no incluye acceso a este módulo."

    def has_permission(self, request, view):
        # Buscar el módulo requerido en la vista (si está definido)
        codigo_modulo = getattr(view, 'modulo_requerido', None)
        
        if not codigo_modulo:
            # Si la vista no define un módulo específico, permitimos el paso
            # O puedes lanzar un error de configuración según la estrictez deseada.
            return True
            
        if not usuario_tiene_modulo(request.user, codigo_modulo):
            self.message = f"Tu plan actual no incluye acceso al módulo: {codigo_modulo}."
            return False
            
        return True
