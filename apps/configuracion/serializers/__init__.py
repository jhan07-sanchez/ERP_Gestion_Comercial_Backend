# apps/configuracion/serializers/__init__.py
"""
Exportaciones centralizadas de serializers de Configuración

¿Por qué este archivo?
Permite importar desde 'apps.configuracion.serializers' directamente,
sin necesidad de saber si el serializer está en read.py o write.py.

Ejemplo de uso:
    from apps.configuracion.serializers import (
        ConfiguracionReadSerializer,
        ConfiguracionUpdateSerializer,
    )
"""

from apps.configuracion.serializers.read import (
    ConfiguracionReadSerializer,
    ConfiguracionResumenSerializer,
)

from apps.configuracion.serializers.write import (
    ConfiguracionUpdateSerializer,
    ResetConsecutivoSerializer,
)

__all__ = [
    "ConfiguracionReadSerializer",
    "ConfiguracionResumenSerializer",
    "ConfiguracionUpdateSerializer",
    "ResetConsecutivoSerializer",
]
