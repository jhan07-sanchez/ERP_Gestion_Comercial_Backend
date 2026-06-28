from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django_filters.rest_framework import DjangoFilterBackend

from apps.facturacion.models import NotaCredito, Factura
from apps.facturacion.serializers.nota_credito import (
    NotaCreditoListSerializer, NotaCreditoDetailSerializer,
    NotaCreditoCreateSerializer, EmitirNotaCreditoSerializer,
    AnularNotaCreditoSerializer
)
from apps.facturacion.services.nota_credito_service import NotaCreditoService


class NotaCreditoViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Notas de Crédito.

    Endpoints generados:
        - GET    /notas-credito/          → Listado con filtros, búsqueda y ordenamiento.
        - POST   /notas-credito/          → Crear borrador de NC.
        - GET    /notas-credito/{id}/      → Detalle completo de una NC.
        - POST   /notas-credito/{id}/emitir/   → Emitir NC (saldo a favor o reembolso).
        - POST   /notas-credito/{id}/anular/   → Anular NC emitida.

    Permisos:
        - Requiere autenticación JWT.
        - DjangoModelPermissions para CRUD estándar.
        - has_perm('facturacion.emitir_factura') para emitir.
        - has_perm('facturacion.anular_factura') para anular.
    """
    permission_classes = [IsAuthenticated, DjangoModelPermissions]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado', 'factura']
    search_fields = ['numero', 'motivo', 'factura__numero']
    ordering_fields = ['fecha_emision', 'total']
    ordering = ['-fecha_emision']

    def get_queryset(self):
        queryset = NotaCredito.objects.all()
        if self.action == 'list':
            return queryset.select_related('factura', 'creado_por')
        return queryset.select_related('factura', 'creado_por').prefetch_related('detalles__producto')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotaCreditoListSerializer
        elif self.action == 'create':
            return NotaCreditoCreateSerializer
        return NotaCreditoDetailSerializer

    def create(self, request, *args, **kwargs):
        """Crea una Nota de Crédito en estado BORRADOR."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data
        try:
            factura = Factura.objects.get(pk=datos['factura_id'])
            nota_credito = NotaCreditoService.crear_borrador(
                factura=factura,
                motivo=datos['motivo'],
                detalles_data=datos['detalles'],
                usuario=request.user
            )
            return Response(
                NotaCreditoDetailSerializer(nota_credito).data,
                status=status.HTTP_201_CREATED
            )
        except Factura.DoesNotExist:
            return Response(
                {"error": "Factura no encontrada."},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def emitir(self, request, pk=None):
        """Emite una NC aplicando la política financiera elegida."""
        if not request.user.has_perm('facturacion.emitir_factura'):
            return Response(
                {"detail": "No tienes permiso para emitir documentos."},
                status=status.HTTP_403_FORBIDDEN
            )

        nota_credito = self.get_object()
        serializer = EmitirNotaCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data
        try:
            nc = NotaCreditoService.emitir(
                nota_credito=nota_credito,
                usuario=request.user,
                tipo_aplicacion=datos['tipo_aplicacion'],
                revertir_inventario=datos['revertir_inventario']
            )
            return Response({
                "status": "Nota de Crédito emitida correctamente.",
                "numero": nc.numero,
                "tipo_aplicacion": datos['tipo_aplicacion']
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Anula una NC emitida."""
        if not request.user.has_perm('facturacion.anular_factura'):
            return Response(
                {"detail": "No tienes permiso para anular documentos."},
                status=status.HTTP_403_FORBIDDEN
            )

        nota_credito = self.get_object()
        serializer = AnularNotaCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            NotaCreditoService.anular(
                nota_credito=nota_credito,
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )
            return Response({"status": "Nota de Crédito anulada correctamente."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
