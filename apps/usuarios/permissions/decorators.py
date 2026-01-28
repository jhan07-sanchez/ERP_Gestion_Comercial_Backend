from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from .helpers import tiene_alguno_de_estos_roles


def requiere_rol(*roles):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Autenticación requerida'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not tiene_alguno_de_estos_roles(request.user, roles):
                return Response(
                    {'error': 'No tienes permisos'},
                    status=status.HTTP_403_FORBIDDEN
                )

            return func(request, *args, **kwargs)
        return wrapper
    return decorator
