# apps/proveedores/serializers/__init__.py
"""
Importar y exportar todos los serializers de Proveedores

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Proveedor
    ProveedorListSerializer,
    ProveedorDetailSerializer,
    ProveedorSimpleSerializer,
)

from .write import (
    # Proveedor
    ProveedorCreateSerializer,
    ProveedorUpdateSerializer,
    ProveedorActivateSerializer,
)

__all__ = [
    # READ - Proveedor
    'ProveedorListSerializer',
    'ProveedorDetailSerializer',
    'ProveedorSimpleSerializer',
    
    # WRITE - Proveedor
    'ProveedorCreateSerializer',
    'ProveedorUpdateSerializer',
    'ProveedorActivateSerializer',
]