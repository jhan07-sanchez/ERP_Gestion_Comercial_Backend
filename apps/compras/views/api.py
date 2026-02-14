# apps/compras/views/api.py
"""
ViewSets para la API de Compras

Este archivo contiene los ViewSets para:
- Compras
- Detalles de Compra

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

from apps.compras.models import Compra, DetalleCompra
from apps.compras.serializers import (
    # Read
    CompraListSerializer,
    CompraDetailSerializer,
    DetalleCompraReadSerializer,
    # Write
    CompraCreateSerializer,
    CompraUpdateSerializer,
    CompraAnularSerializer,
)
from apps.compras.services import CompraService

from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsAlmacenista,
    PuedeGestionarCompras,
    PuedeEliminar,
)


# ============================================================================
# VIEWSET DE COMPRAS
# ============================================================================

class CompraViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar compras
    
    Endpoints:
    - list: GET /api/compras/
    - create: POST /api/compras/
    - retrieve: GET /api/compras/{id}/
    - update: PUT /api/compras/{id}/
    - partial_update: PATCH /api/compras/{id}/
    - destroy: DELETE /api/compras/{id}/
    - anular: POST /api/compras/{id}/anular/
    - estadisticas: GET /api/compras/{id}/estadisticas/
    - resumen: GET /api/compras/resumen/
    - por_proveedor: GET /api/compras/por_proveedor/
    
    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear: Almacenista o superior
    - Actualizar: Almacenista o superior
    - Eliminar/Anular: Solo Supervisor o Admin
    """
    queryset = Compra.objects.select_related('usuario').prefetch_related('detalles')
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return CompraListSerializer
        elif self.action == 'create':
            return CompraCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CompraUpdateSerializer
        elif self.action == 'anular':
            return CompraAnularSerializer
        return CompraDetailSerializer
    
    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['list', 'retrieve']:
            permission_classes = [IsAuthenticated, EsAlmacenista]
        
        elif self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, PuedeGestionarCompras]
        
        elif self.action in ['destroy', 'anular']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        elif self.action in ['estadisticas', 'resumen']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrar compras según parámetros"""
        queryset = Compra.objects.select_related('usuario').prefetch_related(
            'detalles__producto'
        )
        
        # Filtro por proveedor
        proveedor_id = self.request.query_params.get('proveedor_id', None)
        if proveedor_id:
            queryset = queryset.filter(proveedor_id=proveedor_id)
    
        proveedor_nombre = self.request.query_params.get('proveedor', None)
        if proveedor_nombre:
            queryset = queryset.filter(proveedor__nombre__icontains=proveedor_nombre)
        
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
                Q(proveedor__icontains=search) |
                Q(id__icontains=search)
            )
        
        return queryset.order_by('-fecha')
    
    def create(self, request, *args, **kwargs):
        """Crear compra usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            compra = CompraService.crear_compra(
                proveedor=serializer.validated_data['proveedor'],
                detalles=serializer.validated_data['detalles'],
                usuario=request.user,
                fecha=serializer.validated_data['fecha'],
                estado='PENDIENTE'
            )
            
            response_serializer = CompraDetailSerializer(compra)
            return Response(
                {
                    'detail': 'Compra creada exitosamente',
                    'compra': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Actualizar compra (solo proveedor)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            serializer.save()
            response_serializer = CompraDetailSerializer(instance)
            return Response(
                {
                    'detail': 'Compra actualizada exitosamente',
                    'compra': response_serializer.data
                }
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminar compra (con validación de stock)
        
        DELETE /api/compras/{id}/
        """
        instance = self.get_object()
        
        try:
            CompraService.anular_compra(
                compra_id=instance.id,
                usuario=request.user,
                motivo='Eliminación directa'
            )
            
            return Response(
                {'detail': 'Compra eliminada exitosamente.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """
        Anular una compra
        
        POST /api/compras/{id}/anular/
        Body: {
            "motivo": "Motivo de la anulación"
        }
        """
        compra = self.get_object()
        serializer = CompraAnularSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            compra = CompraService.anular_compra(
                compra_id=compra.id,
                usuario=request.user,
                motivo=serializer.validated_data['motivo']
            )
            response_serializer = CompraDetailSerializer(compra)
            return Response({
                'detail': 'Compra anulada exitosamente',
                'compra': response_serializer.data
            })
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
        Obtener estadísticas de una compra
        
        GET /api/compras/{id}/estadisticas/
        """
        try:
            estadisticas = CompraService.obtener_estadisticas_compra(pk)
            return Response(estadisticas)
        except Compra.DoesNotExist:
            return Response(
                {'error': 'Compra no encontrada.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """
        Obtener resumen general de compras
        
        GET /api/compras/resumen/
        
        Query params:
        - fecha_inicio: Fecha inicial (YYYY-MM-DD)
        - fecha_fin: Fecha final (YYYY-MM-DD)
        """
        fecha_inicio = request.query_params.get('fecha_inicio', None)
        fecha_fin = request.query_params.get('fecha_fin', None)
        
        try:
            estadisticas = CompraService.obtener_estadisticas_generales(
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            return Response(estadisticas)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Acción personalizada para marcar una compra como confirmada (realizada)
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):

        compra = self.get_object()

        try:
            compra = CompraService.marcar_como_realizada(
                compra_id=compra.id,
                usuario=request.user
            )

            serializer = CompraDetailSerializer(compra)

            return Response({
            "detail": "Compra confirmada exitosamente",
            "compra": serializer.data
            })

        except ValueError as e:
            return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

    
    @action(detail=False, methods=['get'])
    def por_proveedor(self, request):
        """
        Obtener compras de un proveedor específico
    
        GET /api/compras/compras/por_proveedor/?proveedor_id=1
        """
        proveedor_id = request.query_params.get('proveedor_id', None)
    
        if not proveedor_id:
            return Response(
                {'error': 'El parámetro "proveedor_id" es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        try:
            proveedor_id = int(proveedor_id)
        except ValueError:
            return Response(
                {'error': 'El proveedor_id debe ser un número.'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
        compras = CompraService.obtener_compras_por_proveedor(proveedor_id)
        serializer = CompraListSerializer(compras, many=True)
    
        # Obtener información del proveedor
        if compras.exists():
            proveedor_nombre = compras.first().proveedor.nombre
        else:
            from apps.proveedores.models import Proveedor
        try:
            proveedor = Proveedor.objects.get(id=proveedor_id)
            proveedor_nombre = proveedor.nombre
        except Proveedor.DoesNotExist:
            return Response(
                {'error': 'Proveedor no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
        return Response({
            'proveedor_id': proveedor_id,
            'proveedor_nombre': proveedor_nombre,
            'count': compras.count(),
            'total_invertido': compras.aggregate(total=Sum('total'))['total'] or 0,
            'compras': serializer.data
    })
        
        

# ============================================================================
# VIEWSET DE DETALLES DE COMPRA (Solo lectura)
# ============================================================================

class DetalleCompraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar detalles de compra (Solo lectura)
    
    Endpoints:
    - list: GET /api/compras/detalles/
    - retrieve: GET /api/compras/detalles/{id}/
    
    Permisos:
    - Ver: Almacenista o superior
    
    Nota: Los detalles se crean automáticamente con la compra
    y no se pueden modificar directamente.
    """
    queryset = DetalleCompra.objects.select_related('compra', 'producto')
    serializer_class = DetalleCompraReadSerializer
    permission_classes = [IsAuthenticated, EsAlmacenista]
    
    def get_queryset(self):
        """Filtrar detalles según parámetros"""
        queryset = DetalleCompra.objects.select_related(
            'compra__usuario',
            'producto__categoria'
        )
        
        # Filtro por compra
        compra_id = self.request.query_params.get('compra_id', None)
        if compra_id:
            queryset = queryset.filter(compra_id=compra_id)
        
        # Filtro por producto
        producto_id = self.request.query_params.get('producto_id', None)
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)
        
        return queryset.order_by('-compra__fecha')