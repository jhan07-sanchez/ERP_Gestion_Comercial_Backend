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
from apps.auditorias.mixins import MixinAuditable
from apps.auditorias.services.auditoria_service import AuditoriaService

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
    EsSupervisor,
    EsVendedor,
)


# ============================================================================
# VIEWSET DE CLIENTES
# ============================================================================

class ClienteViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet para gestionar clientes
    """
    queryset = Cliente.objects.all()
    modulo_auditoria = 'CLIENTES'
    
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
        numero_documento = self.request.query_params.get('numero_documento', None)
        if numero_documento:
            queryset = queryset.filter(numero_documento__icontains=numero_documento)
        
        # Búsqueda general
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) |
                Q(numero_documento__icontains=search) |
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
                nombre=serializer.validated_data["nombre"],
                tipo_documento=serializer.validated_data["tipo_documento"],
                numero_documento=serializer.validated_data["numero_documento"],
                telefono=serializer.validated_data.get("telefono"),
                email=serializer.validated_data.get("email"),
                direccion=serializer.validated_data.get("direccion"),
                estado=serializer.validated_data.get("estado", True),
            )
            
            response_serializer = ClienteDetailSerializer(cliente)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='CREAR',
                modulo=self.modulo_auditoria,
                objeto=cliente,
                descripcion=f"Cliente creado: {cliente.nombre}",
                request=request
            )

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
            old_data = self.snapshot_objeto(instance)
            
            cliente = ClienteService.actualizar_cliente(
                pk=instance.pk,
                nombre=serializer.validated_data.get("nombre"),
                telefono=serializer.validated_data.get("telefono"),
                email=serializer.validated_data.get("email"),
                direccion=serializer.validated_data.get("direccion"),
                estado=serializer.validated_data.get("estado"),
            )
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=cliente,
                descripcion=f"Cliente actualizado: {cliente.nombre}",
                request=request,
                datos_antes=old_data,
                datos_despues=self.snapshot_objeto(cliente)
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
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=cliente,
                descripcion=f"Cliente desactivado: {cliente.nombre}",
                request=request
            )

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
                'numero_documento': cliente.numero_documento,
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
                'numero_documento': cliente.numero_documento,
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