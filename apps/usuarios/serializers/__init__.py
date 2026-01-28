# apps/usuarios/serializers/__init__.py
from .read import (
    RolReadSerializer,
    UsuarioRolReadSerializer,
    UsuarioListSerializer,
    UsuarioDetailSerializer,
    UsuarioMeSerializer
)

from .write import (
    RolWriteSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    ChangePasswordSerializer,
    UsuarioActivateSerializer
)

from .jwt import (
    CustomTokenObtainPairSerializer,
    CustomTokenObtainPairView
)

__all__ = [
    # Read
    'RolReadSerializer',
    'UsuarioRolReadSerializer',
    'UsuarioListSerializer',
    'UsuarioDetailSerializer',
    'UsuarioMeSerializer',
    # Write
    'RolWriteSerializer',
    'UsuarioCreateSerializer',
    'UsuarioUpdateSerializer',
    'ChangePasswordSerializer',
    'UsuarioActivateSerializer',
    # JWT
    'CustomTokenObtainPairSerializer',
    'CustomTokenObtainPairView',
]