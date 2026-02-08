# apps/proveedores/views/api.py
"""
ViewSets para la API de Proveedores

Este archivo contiene los ViewSets para:
- Proveedores

Los ViewSets utilizan:
- Serializers (read y write)
- Services (lógica de negocio)
- Permissions (control de acceso)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.proveedores.models import Proveedor
from apps.proveedores.serializers import (
    # Read
    ProveedorListSerializer,
    ProveedorDetailSerializer,
    # Write
    ProveedorCreateSerializer,
    ProveedorUpdateSerializer,
    ProveedorActivateSerializer,
)
from apps.proveedores.services import ProveedorService

from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsAlmacenista,
    PuedeGestionarCompras,
)


# ============================================================================
# VIEWSET DE PROVEEDORES
# ============================================================================

class ProveedorViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar proveedores
    
    Endpoints:
    - list: GET /api/proveedores/
    - create: POST /api/proveedores/
    - retrieve: GET /api/proveedores/{id}/
    - update: PUT /api/proveedores/{id}/
    - partial_update: PATCH /api/proveedores/{id}/
    - destroy: DELETE /api/proveedores/{id}/
    - activar: POST /api/proveedores/{id}/activar/
    - desactivar: POST /api/proveedores/{id}/desactivar/
    - estadisticas: GET /api/proveedores/{id}/estadisticas/
    - frecuentes: GET /api/proveedores/frecuentes/
    - mejores: GET /api/proveedores/mejores/
    - inactivos: GET /api/proveedores/inactivos/
    - buscar: GET /api/proveedores/buscar/
    
    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear/Actualizar: Almacenista o superior
    - Eliminar: Solo Supervisor o Admin
    - Activar/Desactivar: Supervisor o Admin
    - Estadísticas: Supervisor o Admin
    """
    queryset = Proveedor.objects.all()
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return ProveedorListSerializer
        elif self.action == 'create':
            return ProveedorCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ProveedorUpdateSerializer
        elif self.action in ['activar', 'desactivar']:
            return ProveedorActivateSerializer
        return ProveedorDetailSerializer
    
    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['list', 'retrieve', 'buscar']:
            permission_classes = [IsAuthenticated, EsAlmacenista]
        
        elif self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, PuedeGestionarCompras]
        
        elif self.action in ['destroy', 'activar', 'desactivar']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        elif self.action in ['estadisticas', 'frecuentes', 'mejores', 'inactivos']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrar proveedores según parámetros"""
        queryset = Proveedor.objects.all()
        
        # Filtro por estado
        estado = self.request.query_params.get('estado', None)
        if estado is not None:
            queryset = queryset.filter(estado=estado.lower() == 'true')
        
        # Filtro por nombre
        nombre = self.request.query_params.get('nombre', None)
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)
        
        # Filtro por documento
        documento = self.request.query_params.get('documento', None)
        if documento:
            queryset = queryset.filter(documento__icontains=documento)
        
        # Búsqueda general
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(documento__icontains=search) |
                Q(email__icontains=search) |
                Q(telefono__icontains=search)
            )
        
        return queryset.order_by('-fecha_creacion')
    
    def create(self, request, *args, **kwargs):
        """Crear proveedor usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            proveedor = ProveedorService.crear_proveedor(
                nombre=serializer.validated_data['nombre'],
                documento=serializer.validated_data['documento'],
                telefono=serializer.validated_data.get('telefono'),
                email=serializer.validated_data.get('email'),
                direccion=serializer.validated_data.get('direccion'),
                estado=serializer.validated_data.get('estado', True)
            )
            
            response_serializer = ProveedorDetailSerializer(proveedor)
            return Response(
                {
                    'detail': 'Proveedor creado exitosamente',
                    'proveedor': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Actualizar proveedor usando el servicio"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            proveedor = ProveedorService.actualizar_proveedor(
                proveedor_id=instance.id,
                nombre=serializer.validated_data.get('nombre'),
                telefono=serializer.validated_data.get('telefono'),
                email=serializer.validated_data.get('email'),
                direccion=serializer.validated_data.get('direccion'),
                estado=serializer.validated_data.get('estado')
            )
            
            response_serializer = ProveedorDetailSerializer(proveedor)
            return Response(
                {
                    'detail': 'Proveedor actualizado exitosamente',
                    'proveedor': response_serializer.data
                }
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminar proveedor (solo si no tiene compras)
        
        DELETE /api/proveedores/{id}/
        """
        instance = self.get_object()
        
        # Verificar si tiene compras
        if hasattr(instance, 'compras') and instance.compras.exists():
            return Response(
                {
                    'error': 'No se puede eliminar el proveedor porque tiene compras registradas. '
                             'Considere desactivarlo en su lugar.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        
        return Response(
            {'detail': 'Proveedor eliminado exitosamente.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """
        Activar un proveedor
        
        POST /api/proveedores/{id}/activar/
        """
        try:
            proveedor = ProveedorService.activar_proveedor(pk)
            return Response(
                {
                    'detail': f'Proveedor {proveedor.nombre} activado exitosamente.',
                    'proveedor': ProveedorDetailSerializer(proveedor).data
                }
            )
        except Proveedor.DoesNotExist:
            return Response(
                {'error': 'Proveedor no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """
        Desactivar un proveedor
        
        POST /api/proveedores/{id}/desactivar/
        """
        try:
            proveedor = ProveedorService.desactivar_proveedor(pk)
            return Response(
                {
                    'detail': f'Proveedor {proveedor.nombre} desactivado exitosamente.',
                    'proveedor': ProveedorDetailSerializer(proveedor).data
                }
            )
        except Proveedor.DoesNotExist:
            return Response(
                {'error': 'Proveedor no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas detalladas de un proveedor
        
        GET /api/proveedores/{id}/estadisticas/
        """
        try:
            estadisticas = ProveedorService.obtener_estadisticas_proveedor(pk)
            return Response(estadisticas)
        except Proveedor.DoesNotExist:
            return Response(
                {'error': 'Proveedor no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def frecuentes(self, request):
        """
        Obtener proveedores más frecuentes
        
        GET /api/proveedores/frecuentes/?limite=10
        """
        limite = int(request.query_params.get('limite', 10))
        proveedores = ProveedorService.obtener_proveedores_frecuentes(limite)
        
        data = []
        for proveedor in proveedores:
            data.append({
                'id': proveedor.id,
                'nombre': proveedor.nombre,
                'documento': proveedor.documento,
                'total_compras': proveedor.total_compras,
                'total_comprado': float(proveedor.total_comprado) if proveedor.total_comprado else 0
            })
        
        return Response({
            'count': len(data),
            'proveedores': data
        })
    
    @action(detail=False, methods=['get'])
    def mejores(self, request):
        """
        Obtener mejores proveedores (por monto comprado)
        
        GET /api/proveedores/mejores/?limite=10
        """
        limite = int(request.query_params.get('limite', 10))
        proveedores = ProveedorService.obtener_mejores_proveedores(limite)
        
        data = []
        for proveedor in proveedores:
            data.append({
                'id': proveedor.id,
                'nombre': proveedor.nombre,
                'documento': proveedor.documento,
                'total_compras': proveedor.total_compras,
                'total_comprado': float(proveedor.total_comprado) if proveedor.total_comprado else 0
            })
        
        return Response({
            'count': len(data),
            'proveedores': data
        })
    
    @action(detail=False, methods=['get'])
    def inactivos(self, request):
        """
        Obtener proveedores inactivos (sin compras en X días)
        
        GET /api/proveedores/inactivos/?dias=30
        """
        dias = int(request.query_params.get('dias', 30))
        proveedores = ProveedorService.obtener_proveedores_inactivos(dias)
        serializer = ProveedorListSerializer(proveedores, many=True)
        
        return Response({
            'dias_inactividad': dias,
            'count': proveedores.count(),
            'proveedores': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Buscar proveedores
        
        GET /api/proveedores/buscar/?q=texto
        """
        query = request.query_params.get('q', '')
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'El parámetro "q" debe tener al menos 2 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        proveedores = ProveedorService.buscar_proveedores(query)
        serializer = ProveedorListSerializer(proveedores, many=True)
        
        return Response({
            'query': query,
            'count': proveedores.count(),
            'proveedores': serializer.data
        })