"""
Inicialización del módulo de vistas - App Precio

¿Por qué existe este archivo?
──────────────────────────────
Permite importar los ViewSets de forma limpia desde:

    from apps.precio.views import ListaPrecioCompraViewSet

en lugar de:

    from apps.precio.views.api import ListaPrecioCompraViewSet

Esto mejora la legibilidad y mantiene la arquitectura modular.
"""

from .api import ListaPrecioCompraViewSet

__all__ = [
    "ListaPrecioCompraViewSet",
]
