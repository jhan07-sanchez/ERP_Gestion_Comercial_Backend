from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django_filters.rest_framework import DjangoFilterBackend
from apps.facturacion.models import PagoFactura
from apps.facturacion.serializers.pago import PagoFacturaSerializer

class PagoFacturaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint para listar y ver detalles de pagos recibidos.
    La creación se realiza mediante la acción 'registrar_pago' en FacturaViewSet.
    """
    queryset = PagoFactura.objects.select_related(
        'factura', 'factura__cliente', 'metodo_pago', 'registrado_por'
    ).all()
    serializer_class = PagoFacturaSerializer
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['factura__estado', 'metodo_pago']
    search_fields = ['factura__numero', 'factura__cliente__nombre', 'referencia']
    ordering_fields = ['fecha', 'monto']
    ordering = ['-fecha']

