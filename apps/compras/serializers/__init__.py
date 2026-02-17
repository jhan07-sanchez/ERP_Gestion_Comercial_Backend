# apps/compras/serializers/__init__.py
"""
Importar y exportar todos los serializers de Compras

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Simples
    ProductoCompraSerializer,
    # Detalle de Compra
    DetalleCompraReadSerializer,
    # Compra
    CompraListSerializer,
    CompraDetailSerializer,
    CompraSimpleSerializer,
)

from .write import (
    # Detalle de Compra
    DetalleCompraWriteSerializer,
    
    # Compra
    CompraCreateSerializer,
    CompraUpdateSerializer,
    CompraAnularSerializer,
)

__all__ = [
    # READ - Simples
    'ProductoCompraSerializer',
    
    # READ - Detalle de Compra
    'DetalleCompraReadSerializer',
    
    # READ - Compra
    'CompraListSerializer',
    'CompraDetailSerializer',
    'CompraSimpleSerializer',
    
    # WRITE - Detalle de Compra
    'DetalleCompraWriteSerializer',
    
    # WRITE - Compra
    'CompraCreateSerializer',
    'CompraUpdateSerializer',
    'CompraAnularSerializer',
]