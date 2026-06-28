from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.facturacion.views.factura_views import FacturaViewSet
from apps.facturacion.views.dashboard_views import DashboardFacturacionViewSet
from apps.facturacion.views.nota_credito_api import NotaCreditoViewSet
from apps.facturacion.views.nota_debito_api import NotaDebitoViewSet
from apps.facturacion.views.pago_views import PagoFacturaViewSet
router = DefaultRouter()
router.register(r'facturas', FacturaViewSet, basename='factura')
router.register(r'notas-credito', NotaCreditoViewSet, basename='notacredito')
router.register(r'notas-debito', NotaDebitoViewSet, basename='notadebito')
router.register(r'dashboard', DashboardFacturacionViewSet, basename='dashboard')
router.register(r'pagos', PagoFacturaViewSet, basename='pagofactura')
urlpatterns = [
    path('', include(router.urls)),
]
