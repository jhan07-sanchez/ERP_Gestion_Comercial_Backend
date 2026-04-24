# apps/precio/serializers/__init__.py
"""
¿Por qué existe este __init__.py?
──────────────────────────────────
Sin este archivo, Python no reconoce la carpeta 'serializers' como
un módulo importable. Con este archivo, cualquier parte del proyecto
puede importar así:

    from apps.precio.serializers import ListaPrecioCompraListSerializer

En lugar de tener que escribir:
    from apps.precio.serializers.read import ListaPrecioCompraListSerializer

Es simplemente comodidad y organización.
"""

from .read import (
    ListaPrecioCompraListSerializer,
    ListaPrecioCompraDetailSerializer,
    ListaPrecioCompraSimpleSerializer,
)

from .write import (
    ListaPrecioCompraCreateSerializer,
    ListaPrecioCompraUpdateSerializer,
)

__all__ = [
    # READ
    "ListaPrecioCompraListSerializer",
    "ListaPrecioCompraDetailSerializer",
    "ListaPrecioCompraSimpleSerializer",
    # WRITE
    "ListaPrecioCompraCreateSerializer",
    "ListaPrecioCompraUpdateSerializer",
]
