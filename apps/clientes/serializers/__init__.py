# apps/clientes/serializers/__init__.py
"""
Importar y exportar todos los serializers de Clientes

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Cliente
    ClienteListSerializer,
    ClienteDetailSerializer,
    ClienteSimpleSerializer,
)

from .write import (
    # Cliente
    ClienteCreateSerializer,
    ClienteUpdateSerializer,
    ClienteActivateSerializer,
)

__all__ = [
    # READ - Cliente
    'ClienteListSerializer',
    'ClienteDetailSerializer',
    'ClienteSimpleSerializer',
    
    # WRITE - Cliente
    'ClienteCreateSerializer',
    'ClienteUpdateSerializer',
    'ClienteActivateSerializer',
]