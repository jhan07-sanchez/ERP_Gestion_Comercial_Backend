# apps/categorias/serializers/__init__.py
"""
Importar y exportar todos los serializers de Categorías

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    CategoriaReadSerializer,
    CategoriaSimpleSerializer,
)

from .write import (
    CategoriaWriteSerializer,
)

__all__ = [
    # READ
    'CategoriaReadSerializer',
    'CategoriaSimpleSerializer',

    # WRITE
    'CategoriaWriteSerializer',
]
