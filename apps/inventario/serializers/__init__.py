# apps/inventario/serializers/__init__.py
"""
Importar y exportar todos los serializers de Inventario

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Inventario
    InventarioReadSerializer,

    # Movimientos
    MovimientoInventarioReadSerializer,
)

from .write import (
    # Movimientos
    MovimientoInventarioCreateSerializer,
)

__all__ = [
    # READ - Inventario
    'InventarioReadSerializer',

    # READ - Movimientos
    'MovimientoInventarioReadSerializer',

    # WRITE - Movimientos
    'MovimientoInventarioCreateSerializer',
]