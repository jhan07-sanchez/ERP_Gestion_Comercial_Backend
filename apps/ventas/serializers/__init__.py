# apps/ventas/serializers/__init__.py
"""
Importar y exportar todos los serializers de Ventas

Organización:
- read.py: Serializers de lectura (GET)
- write.py: Serializers de escritura (POST, PUT, PATCH)
"""

from .read import (
    # Simples
    ClienteSimpleSerializer,
    ProductoSimpleSerializer,
    
    # Detalle de Venta
    DetalleVentaReadSerializer,
    
    # Venta
    VentaListSerializer,
    VentaDetailSerializer,
    VentaSimpleSerializer,
)

from .write import (
    # Detalle de Venta
    DetalleVentaWriteSerializer,
    
    # Venta
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaCancelarSerializer,
    VentaCompletarSerializer,
)

__all__ = [
    # READ - Simples
    'ClienteSimpleSerializer',
    'ProductoSimpleSerializer',
    
    # READ - Detalle de Venta
    'DetalleVentaReadSerializer',
    
    # READ - Venta
    'VentaListSerializer',
    'VentaDetailSerializer',
    'VentaSimpleSerializer',
    
    # WRITE - Detalle de Venta
    'DetalleVentaWriteSerializer',
    
    # WRITE - Venta
    'VentaCreateSerializer',
    'VentaUpdateSerializer',
    'VentaCancelarSerializer',
    'VentaCompletarSerializer',
]