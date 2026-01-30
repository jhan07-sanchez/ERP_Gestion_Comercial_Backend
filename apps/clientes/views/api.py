# apps/clientes/views/api.py
"""
ViewSets para la API de Clientes

Este archivo contiene los ViewSets para:
- Clientes

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

from apps.clientes.models import Cliente
from apps.clientes.serializers import (
    # Read
    ClienteListSerializer,
    ClienteDetailSerializer,
    # Write
    ClienteCreateSerializer,
    ClienteUpdateSerializer,
    ClienteActivateSerializer,
)
from apps.clientes.services import ClienteService

from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsVendedor,
)


# ============================================================================
# VIEWSET DE CLIENTES
# ============================================================================

class ClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    
    Endpoints:
    - list: GET /api/clientes/
    - create: POST /api/clientes/
    - retrieve: GET /api/clientes/{id}/
    - update: PUT /api/clientes/{id}/
    - partial_update: PATCH /api/clientes/{id}/
    - destroy: DELETE /api/clientes/{id}/
    - activar: POST /api/clientes/{id}/activar/
    - desactivar: POST /api/clientes/{id}/desactivar/
    - estadisticas: GET /api/clientes/{id}/estadisticas/
    - frecuentes: GET /api/clientes/frecuentes/
    - mejores: GET /api/clientes/mejores/
    - inactivos: GET /api/clientes/inactivos/
    - buscar: GET /api/clientes/buscar/
    
    Permisos:
    - Listar/Ver: Vendedor o superior
    - Crear/Actualizar: Vendedor o superior
    - Eliminar: Solo Supervisor o Admin
    - Activar/Desactivar: Supervisor o Admin
    - Estadísticas: Supervisor o Admin
    """
    queryset = Cliente.objects.all()
    
    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'list':
            return ClienteListSerializer
        elif self.action == 'create':
            return ClienteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClienteUpdateSerializer
        elif self.action in ['activar', 'desactivar']:
            return ClienteActivateSerializer
        return ClienteDetailSerializer
    
    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ['list', 'retrieve', 'buscar']:
            permission_classes = [IsAuthenticated, EsVendedor]
        
        elif self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsAuthenticated, EsVendedor]
        
        elif self.action in ['destroy', 'activar', 'desactivar']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        elif self.action in ['estadisticas', 'frecuentes', 'mejores', 'inactivos']:
            permission_classes = [IsAuthenticated, EsSupervisor]
        
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filtrar clientes según parámetros"""
        queryset = Cliente.objects.all()
        
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
        """Crear cliente usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            cliente = ClienteService.crear_cliente(
                nombre=serializer.validated_data['nombre'],
                documento=serializer.validated_data['documento'],
                telefono=serializer.validated_data.get('telefono'),
                email=serializer.validated_data.get('email'),
                direccion=serializer.validated_data.get('direccion'),
                estado=serializer.validated_data.get('estado', True)
            )
            
            response_serializer = ClienteDetailSerializer(cliente)
            return Response(
                {
                    'detail': 'Cliente creado exitosamente',
                    'cliente': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, *args, **kwargs):
        """Actualizar cliente usando el servicio"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        try:
            cliente = ClienteService.actualizar_cliente(
                cliente_id=instance.id,
                nombre=serializer.validated_data.get('nombre'),
                telefono=serializer.validated_data.get('telefono'),
                email=serializer.validated_data.get('email'),
                direccion=serializer.validated_data.get('direccion'),
                estado=serializer.validated_data.get('estado')
            )
            
            response_serializer = ClienteDetailSerializer(cliente)
            return Response(
                {
                    'detail': 'Cliente actualizado exitosamente',
                    'cliente': response_serializer.data
                }
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Eliminar cliente (solo si no tiene ventas)
        
        DELETE /api/clientes/{id}/
        """
        instance = self.get_object()
        
        # Verificar si tiene ventas
        if hasattr(instance, 'ventas') and instance.ventas.exists():
            return Response(
                {
                    'error': 'No se puede eliminar el cliente porque tiene ventas registradas. '
                             'Considere desactivarlo en su lugar.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        instance.delete()
        
        return Response(
            {'detail': 'Cliente eliminado exitosamente.'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'])
    def activar(self, request, pk=None):
        """
        Activar un cliente
        
        POST /api/clientes/{id}/activar/
        """
        try:
            cliente = ClienteService.activar_cliente(pk)
            return Response(
                {
                    'detail': f'Cliente {cliente.nombre} activado exitosamente.',
                    'cliente': ClienteDetailSerializer(cliente).data
                }
            )
        except Cliente.DoesNotExist:
            return Response(
                {'error': 'Cliente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def desactivar(self, request, pk=None):
        """
        Desactivar un cliente
        
        POST /api/clientes/{id}/desactivar/
        """
        try:
            cliente = ClienteService.desactivar_cliente(pk)
            return Response(
                {
                    'detail': f'Cliente {cliente.nombre} desactivado exitosamente.',
                    'cliente': ClienteDetailSerializer(cliente).data
                }
            )
        except Cliente.DoesNotExist:
            return Response(
                {'error': 'Cliente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas detalladas de un cliente
        
        GET /api/clientes/{id}/estadisticas/
        """
        try:
            estadisticas = ClienteService.obtener_estadisticas_cliente(pk)
            return Response(estadisticas)
        except Cliente.DoesNotExist:
            return Response(
                {'error': 'Cliente no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def frecuentes(self, request):
        """
        Obtener clientes más frecuentes
        
        GET /api/clientes/frecuentes/?limite=10
        """
        limite = int(request.query_params.get('limite', 10))
        clientes = ClienteService.obtener_clientes_frecuentes(limite)
        
        data = []
        for cliente in clientes:
            data.append({
                'id': cliente.id,
                'nombre': cliente.nombre,
                'documento': cliente.documento,
                'total_compras': cliente.total_compras,
                'total_gastado': float(cliente.total_gastado) if cliente.total_gastado else 0
            })
        
        return Response({
            'count': len(data),
            'clientes': data
        })
    
    @action(detail=False, methods=['get'])
    def mejores(self, request):
        """
        Obtener mejores clientes (por monto gastado)
        
        GET /api/clientes/mejores/?limite=10
        """
        limite = int(request.query_params.get('limite', 10))
        clientes = ClienteService.obtener_mejores_clientes(limite)
        
        data = []
        for cliente in clientes:
            data.append({
                'id': cliente.id,
                'nombre': cliente.nombre,
                'documento': cliente.documento,
                'total_compras': cliente.total_compras,
                'total_gastado': float(cliente.total_gastado) if cliente.total_gastado else 0
            })
        
        return Response({
            'count': len(data),
            'clientes': data
        })
    
    @action(detail=False, methods=['get'])
    def inactivos(self, request):
        """
        Obtener clientes inactivos (sin compras en X días)
        
        GET /api/clientes/inactivos/?dias=30
        """
        dias = int(request.query_params.get('dias', 30))
        clientes = ClienteService.obtener_clientes_inactivos(dias)
        serializer = ClienteListSerializer(clientes, many=True)
        
        return Response({
            'dias_inactividad': dias,
            'count': clientes.count(),
            'clientes': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """
        Buscar clientes
        
        GET /api/clientes/buscar/?q=texto
        """
        query = request.query_params.get('q', '')
        
        if not query or len(query) < 2:
            return Response(
                {'error': 'El parámetro "q" debe tener al menos 2 caracteres.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        clientes = ClienteService.buscar_clientes(query)
        serializer = ClienteListSerializer(clientes, many=True)
        
        return Response({
            'query': query,
            'count': clientes.count(),
            'clientes': serializer.data
        })