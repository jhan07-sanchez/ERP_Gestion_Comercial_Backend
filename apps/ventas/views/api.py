# apps/ventas/views/api.py
"""
ViewSets para la API de Ventas

Este archivo contiene los ViewSets para:
- Ventas
- Detalles de Venta

Los ViewSets utilizan:
- Serializers (read y write)
- Services (lógica de negocio)
- Permissions (control de acceso)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum

from apps.ventas.models import Venta, DetalleVenta
from apps.ventas.serializers import (
    # Read
    VentaListSerializer,
    VentaDetailSerializer,
    DetalleVentaReadSerializer,
    # Write
    VentaCreateSerializer,
    VentaUpdateSerializer,
    VentaCancelarSerializer,
    VentaCompletarSerializer,
)
from apps.ventas.services import VentaService

from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsVendedor,
    PuedeGestionarVentas,
    PuedeEliminar,
)


# ============================================================================
# VIEWSET DE VENTAS
# ============================================================================

class VentaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar ventas

    Endpoints:
    - list: GET /api/ventas/
    - create: POST /api/ventas/
    - retrieve: GET /api/ventas/{id}/
    - update: PUT /api/ventas/{id}/
    - partial_update: PATCH /api/ventas/{id}/
    - destroy: DELETE /api/ventas/{id}/
    - completar: POST /api/ventas/{id}/completar/
    - cancelar: POST /api/ventas/{id}/cancelar/
    - estadisticas: GET /api/ventas/{id}/estadisticas/
    - resumen: GET /api/ventas/resumen/
    - pendientes: GET /api/ventas/pendientes/
    - completadas: GET /api/ventas/completadas/

    Permisos:
    - Listar/Ver: Vendedor o superior
    - Crear: Vendedor o superior
    - Actualizar: Vendedor o superior
    - Eliminar: Solo Supervisor o Admin
    - Cancelar: Supervisor o Admin
    - Completar: Vendedor o superior
    """
    queryset = Venta.objects.select_related('cliente', 'usuario').prefetch_related('detalles')

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return VentaListSerializer
        elif self.action == 'create':
            return VentaCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return VentaUpdateSerializer
        elif self.action == 'cancelar':
            return VentaCancelarSerializer
        elif self.action == 'completar':
            return VentaCompletarSerializer
        return VentaDetailSerializer

    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, EsVendedor]

        elif self.action in ['create', 'update', 'partial_update', 'completar']:
            permission_classes = [IsAuthenticated, PuedeGestionarVentas]

        elif self.action in ['destroy', 'cancelar']:
            permission_classes = [IsAuthenticated, EsSupervisor]

        elif self.action in ['estadisticas', 'resumen']:
            permission_classes = [IsAuthenticated, EsSupervisor]

        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filtrar ventas según parámetros"""
        queryset = Venta.objects.select_related('cliente', 'usuario').prefetch_related(
            'detalles__producto'
        )

        # Filtro por cliente
        cliente_id = self.request.query_params.get('cliente_id', None)
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)

        cliente_nombre = self.request.query_params.get('cliente', None)
        if cliente_nombre:
            queryset = queryset.filter(cliente__nombre__icontains=cliente_nombre)

        # Filtro por estado
        estado = self.request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado.upper())

        # Filtro por usuario
        usuario_id = self.request.query_params.get('usuario_id', None)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        # Filtro por fecha
        fecha_inicio = self.request.query_params.get('fecha_inicio', None)
        fecha_fin = self.request.query_params.get('fecha_fin', None)

        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        # Filtro por rango de total
        total_min = self.request.query_params.get('total_min', None)
        total_max = self.request.query_params.get('total_max', None)

        if total_min:
            queryset = queryset.filter(total__gte=total_min)
        if total_max:
            queryset = queryset.filter(total__lte=total_max)

        # Búsqueda general
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(cliente__nombre__icontains=search) |
                Q(cliente__documento__icontains=search) |
                Q(id__icontains=search)
            )

        return queryset.order_by('-fecha')

    def create(self, request, *args, **kwargs):
        """Crear venta usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            venta = VentaService.crear_venta(
                cliente_id=serializer.validated_data['cliente_id'],
                detalles=serializer.validated_data['detalles'],
                usuario=request.user,
                estado=serializer.validated_data.get('estado', 'PENDIENTE')
            )

            response_serializer = VentaDetailSerializer(venta)
            return Response(
                {
                    'detail': 'Venta creada exitosamente',
                    'venta': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Actualizar venta (solo estado)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
            response_serializer = VentaDetailSerializer(instance)
            return Response(
                {
                    'detail': 'Venta actualizada exitosamente',
                    'venta': response_serializer.data
                }
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar venta (solo si está pendiente y no tiene movimientos)

        DELETE /api/ventas/{id}/
        """
        instance = self.get_object()

        # Verificar que esté pendiente
        if instance.estado != 'PENDIENTE':
            return Response(
                {'error': 'Solo se pueden eliminar ventas en estado PENDIENTE.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Eliminar
        instance.delete()

        return Response(
            {'detail': 'Venta eliminada exitosamente.'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """
        Completar una venta pendiente

        POST /api/ventas/{id}/completar/
        Body: {
            "notas": "Notas opcionales"
        }
        """
        venta = self.get_object()
        serializer = VentaCompletarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            venta_completada = VentaService.completar_venta(
                venta_id=venta.id,
                usuario=request.user,
                notas=serializer.validated_data.get('notas')
            )

            response_serializer = VentaDetailSerializer(venta_completada)
            return Response(
                {
                    'detail': 'Venta completada exitosamente',
                    'venta': response_serializer.data
                }
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """
        Cancelar una venta

        POST /api/ventas/{id}/cancelar/
        Body: {
            "motivo": "Motivo de la cancelación"
        }
        """
        venta = self.get_object()
        serializer = VentaCancelarSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            venta_cancelada = VentaService.cancelar_venta(
                venta_id=venta.id,
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )

            response_serializer = VentaDetailSerializer(venta_cancelada)
            return Response(
                {
                    'detail': 'Venta cancelada exitosamente',
                    'venta': response_serializer.data
                }
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas de una venta

        GET /api/ventas/{id}/estadisticas/
        """
        try:
            estadisticas = VentaService.obtener_estadisticas_venta(pk)
            return Response(estadisticas)
        except Venta.DoesNotExist:
            return Response(
                {'error': 'Venta no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """
        Obtener resumen general de ventas

        GET /api/ventas/resumen/

        Query params:
        - fecha_inicio: Fecha inicial (YYYY-MM-DD)
        - fecha_fin: Fecha final (YYYY-MM-DD)
        """
        fecha_inicio = request.query_params.get('fecha_inicio', None)
        fecha_fin = request.query_params.get('fecha_fin', None)

        try:
            estadisticas = VentaService.obtener_estadisticas_generales(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            return Response(estadisticas)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def pendientes(self, request):
        """
        Obtener ventas pendientes

        GET /api/ventas/pendientes/
        """
        ventas = self.get_queryset().filter(estado='PENDIENTE')
        serializer = VentaListSerializer(ventas, many=True)

        return Response({
            'count': ventas.count(),
            'total_pendiente': ventas.aggregate(total=Sum('total'))['total'] or 0,
            'ventas': serializer.data
        })

    @action(detail=False, methods=['get'])
    def completadas(self, request):
        """
        Obtener ventas completadas

        GET /api/ventas/completadas/

        Query params:
        - fecha_inicio: Fecha inicial
        - fecha_fin: Fecha final
        """
        queryset = self.get_queryset().filter(estado='COMPLETADA')

        # Aplicar filtros de fecha si se proporcionan
        fecha_inicio = request.query_params.get('fecha_inicio', None)
        fecha_fin = request.query_params.get('fecha_fin', None)

        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        serializer = VentaListSerializer(queryset, many=True)

        return Response({
            'count': queryset.count(),
            'total_vendido': queryset.aggregate(total=Sum('total'))['total'] or 0,
            'ventas': serializer.data
        })


# ============================================================================
# VIEWSET DE DETALLES DE VENTA (Solo lectura)
# ============================================================================

class DetalleVentaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar detalles de venta (Solo lectura)

    Endpoints:
    - list: GET /api/ventas/detalles/
    - retrieve: GET /api/ventas/detalles/{id}/

    Permisos:
    - Ver: Vendedor o superior

    Nota: Los detalles se crean automáticamente con la venta
    y no se pueden modificar directamente.
    """
    queryset = DetalleVenta.objects.select_related('venta', 'producto')
    serializer_class = DetalleVentaReadSerializer
    permission_classes = [IsAuthenticated, EsVendedor]

    def get_queryset(self):
        """Filtrar detalles según parámetros"""
        queryset = DetalleVenta.objects.select_related(
            'venta__cliente',
            'producto__categoria'
        )

        # Filtro por venta
        venta_id = self.request.query_params.get('venta_id', None)
        if venta_id:
            queryset = queryset.filter(venta_id=venta_id)

        # Filtro por producto
        producto_id = self.request.query_params.get('producto_id', None)
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)

        return queryset.order_by('-venta__fecha')