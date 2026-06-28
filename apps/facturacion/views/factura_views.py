from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from apps.facturacion.models import Factura
from apps.facturacion.serializers.factura_venta import (
    FacturaListSerializer, FacturaDetailSerializer, FacturaCreateSerializer,
    FacturaUpdateSerializer, AnularFacturaSerializer
)
from apps.facturacion.serializers.pago import RegistrarPagoSerializer, PagoFacturaSerializer
from apps.facturacion.services.factura_venta_service import FacturaVentaService
from apps.facturacion.services.pago_factura_service import PagoFacturaService
from apps.auditorias.mixins import MixinAuditable

class FacturaViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    API endpoint que permite ver y editar facturas.
    Optimizada para evitar N+1 queries e incluye filtros y paginación.
    """
    permission_classes = [IsAuthenticated, DjangoModelPermissions]
    modulo_auditoria = "FACTURACION"
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'cliente', 'fecha_emision']
    search_fields = ['numero', 'cliente__nombre', 'cliente__numero_documento']
    ordering_fields = ['fecha_emision', 'total', 'fecha_creacion']
    ordering = ['-fecha_creacion']

    def get_queryset(self):
        """
        Optimización N+1 usando select_related y prefetch_related dependiendo de la acción.
        """
        queryset = Factura.objects.all()
        
        if self.action == 'list':
            return queryset.select_related('cliente')
            
        elif self.action == 'retrieve':
            return queryset.select_related(
                'cliente', 'vendedor', 'creado_por', 'documento'
            ).prefetch_related(
                'detalles__producto', 
                'desglose_impuestos__impuesto', 
                'pagos__metodo_pago',
                'pagos__registrado_por'
            )
            
        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return FacturaListSerializer
        elif self.action == 'create':
            return FacturaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return FacturaUpdateSerializer
        return FacturaDetailSerializer

    def perform_destroy(self, instance):
        """
        Solo se pueden borrar físicamente las facturas en estado BORRADOR.
        """
        from rest_framework.exceptions import ValidationError
        if instance.estado != "BORRADOR":
            raise ValidationError("No se puede eliminar una factura que ya fue emitida. Por favor, utilice la opción de Anular.")
        super().perform_destroy(instance)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        datos = serializer.validated_data
        try:
            factura = FacturaVentaService.crear_borrador(
                cliente_id=datos['cliente_id'],
                vendedor_id=datos.get('vendedor_id'),
                detalles_data=datos['detalles'],
                usuario=request.user,
                fecha_emision=datos.get('fecha_emision'),
                fecha_vencimiento=datos.get('fecha_vencimiento'),
                observaciones=datos.get('observaciones', '')
            )
            
            self.kwargs['pk'] = factura.pk
            response_serializer = FacturaDetailSerializer(factura)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """
        Sobrescribe update para inyectar lógica de negocio de reemplazo total.
        """
        factura = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        datos = serializer.validated_data
        try:
            factura_actualizada = FacturaVentaService.actualizar_borrador(
                factura=factura,
                cliente_id=datos.get('cliente_id', factura.cliente_id),
                vendedor_id=datos.get('vendedor_id', factura.vendedor_id),
                fecha_emision=datos.get('fecha_emision', factura.fecha_emision),
                fecha_vencimiento=datos.get('fecha_vencimiento', factura.fecha_vencimiento),
                observaciones=datos.get('observaciones', factura.observaciones),
                detalles_data=datos.get('detalles', []),
                usuario=request.user
            )
            return Response(FacturaDetailSerializer(factura_actualizada).data, status=status.HTTP_200_OK)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def emitir(self, request, pk=None):
        if not request.user.has_perm('facturacion.emitir_factura'):
            return Response({"detail": "No tienes permiso para emitir facturas."}, status=status.HTTP_403_FORBIDDEN)
            
        factura = self.get_object()
        try:
            FacturaVentaService.emitir_factura(factura, request.user)
            return Response({"status": "Factura emitida correctamente", "numero": factura.numero})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        if not request.user.has_perm('facturacion.anular_factura'):
            return Response({"detail": "No tienes permiso para anular facturas."}, status=status.HTTP_403_FORBIDDEN)
            
        factura = self.get_object()
        serializer = AnularFacturaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            FacturaVentaService.anular_factura(factura, request.user, serializer.validated_data['motivo'])
            return Response({"status": "Factura anulada correctamente"})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def registrar_pago(self, request, pk=None):
        if not request.user.has_perm('facturacion.registrar_pago_factura'):
            return Response({"detail": "No tienes permiso para registrar pagos."}, status=status.HTTP_403_FORBIDDEN)
            
        factura = self.get_object()
        serializer = RegistrarPagoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        datos = serializer.validated_data
        try:
            pago = PagoFacturaService.registrar_pago(
                factura=factura,
                metodo_pago_id=datos['metodo_pago_id'],
                monto=datos['monto'],
                referencia=datos.get('referencia', ''),
                observaciones=datos.get('observaciones', ''),
                usuario=request.user
            )
            return Response(PagoFacturaSerializer(pago).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
