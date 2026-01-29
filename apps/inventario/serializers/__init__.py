# apps/inventario/serializers/__init__.py
"""
Importar y exportar todos los serializers de Inventario

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Categoría
    CategoriaReadSerializer,
    CategoriaSimpleSerializer,
    
    # Producto
    ProductoListSerializer,
    ProductoDetailSerializer,
    ProductoSimpleSerializer,
    
    # Inventario
    InventarioReadSerializer,
    
    # Movimientos
    MovimientoInventarioReadSerializer,
)

from .write import (
    # Categoría
    CategoriaWriteSerializer,
    
    # Producto
    ProductoCreateSerializer,
    ProductoUpdateSerializer,
    ProductoActivateSerializer,
    AjusteInventarioSerializer,
    
    # Movimientos
    MovimientoInventarioCreateSerializer,
)

__all__ = [
    # READ - Categoría
    'CategoriaReadSerializer',
    'CategoriaSimpleSerializer',
    
    # READ - Producto
    'ProductoListSerializer',
    'ProductoDetailSerializer',
    'ProductoSimpleSerializer',
    
    # READ - Inventario
    'InventarioReadSerializer',
    
    # READ - Movimientos
    'MovimientoInventarioReadSerializer',
    
    # WRITE - Categoría
    'CategoriaWriteSerializer',
    
    # WRITE - Producto
    'ProductoCreateSerializer',
    'ProductoUpdateSerializer',
    'ProductoActivateSerializer',
    'AjusteInventarioSerializer',
    
    # WRITE - Movimientos
    'MovimientoInventarioCreateSerializer',
]