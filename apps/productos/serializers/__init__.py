# apps/productos/serializers/__init__.py
"""
Importar y exportar todos los serializers de Productos

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    ProductoListSerializer,
    ProductoDetailSerializer,
    ProductoSimpleSerializer,
)

from .write import (
    ProductoCreateSerializer,
    ProductoUpdateSerializer,
    ProductoActivateSerializer,
    AjusteInventarioSerializer,
)

__all__ = [
    # READ
    'ProductoListSerializer',
    'ProductoDetailSerializer',
    'ProductoSimpleSerializer',

    # WRITE
    'ProductoCreateSerializer',
    'ProductoUpdateSerializer',
    'ProductoActivateSerializer',
    'AjusteInventarioSerializer',
]
