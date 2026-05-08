# apps/dashboard/views/__init__.py
from .api import (
    ResumenGeneralView,
    KpisVentasView,
    KpisComprasView,
    KpisInventarioView,
    KpisClientesView,
    GraficoVentasView,
    GraficoComprasView,
    ProductosTopView,
    ClientesTopView,
    AlertasView,
    ActividadRecienteView,
    GraficoCajaView,
    AnaliticaCompletaView,
)

__all__ = [
    "ResumenGeneralView",
    "KpisVentasView",
    "KpisComprasView",
    "KpisInventarioView",
    "KpisClientesView",
    "GraficoVentasView",
    "GraficoComprasView",
    "ProductosTopView",
    "ClientesTopView",
    "AlertasView",
    "ActividadRecienteView",
    "GraficoCajaView",
    "AnaliticaCompletaView",
]
