from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions
from django_filters.rest_framework import DjangoFilterBackend

from apps.facturacion.models import NotaDebito, Factura
from apps.facturacion.serializers.nota_debito import (
    NotaDebitoListSerializer, NotaDebitoDetailSerializer,
    NotaDebitoCreateSerializer, AnularNotaDebitoSerializer
)
from apps.facturacion.services.nota_debito_service import NotaDebitoService


class NotaDebitoViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar Notas de Débito.

    Endpoints generados:
        - GET    /notas-debito/             → Listado con filtros, búsqueda y ordenamiento.
        - POST   /notas-debito/             → Crear borrador de ND.
        - GET    /notas-debito/{id}/         → Detalle completo de una ND.
        - POST   /notas-debito/{id}/emitir/  → Emitir ND.
        - POST   /notas-debito/{id}/anular/  → Anular ND emitida.

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
        queryset = NotaDebito.objects.all()
        if self.action == 'list':
            return queryset.select_related('factura', 'creado_por')
        return queryset.select_related('factura', 'creado_por').prefetch_related('detalles__producto')

    def get_serializer_class(self):
        if self.action == 'list':
            return NotaDebitoListSerializer
        elif self.action == 'create':
            return NotaDebitoCreateSerializer
        return NotaDebitoDetailSerializer

    def create(self, request, *args, **kwargs):
        """Crea una Nota de Débito en estado BORRADOR."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        datos = serializer.validated_data
        try:
            factura = Factura.objects.get(pk=datos['factura_id'])
            nota_debito = NotaDebitoService.crear_borrador(
                factura=factura,
                motivo=datos['motivo'],
                detalles_data=datos['detalles'],
                usuario=request.user
            )
            return Response(
                NotaDebitoDetailSerializer(nota_debito).data,
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
        """Emite una ND: asigna consecutivo, genera documento e incrementa deuda."""
        if not request.user.has_perm('facturacion.emitir_factura'):
            return Response(
                {"detail": "No tienes permiso para emitir documentos."},
                status=status.HTTP_403_FORBIDDEN
            )

        nota_debito = self.get_object()
        try:
            nd = NotaDebitoService.emitir(
                nota_debito=nota_debito,
                usuario=request.user
            )
            return Response({
                "status": "Nota de Débito emitida correctamente.",
                "numero": nd.numero
            })
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Anula una ND emitida y revierte el incremento de deuda."""
        if not request.user.has_perm('facturacion.anular_factura'):
            return Response(
                {"detail": "No tienes permiso para anular documentos."},
                status=status.HTTP_403_FORBIDDEN
            )

        nota_debito = self.get_object()
        serializer = AnularNotaDebitoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            NotaDebitoService.anular(
                nota_debito=nota_debito,
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )
            return Response({"status": "Nota de Débito anulada correctamente."})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
