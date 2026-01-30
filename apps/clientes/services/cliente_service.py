# apps/clientes/services/cliente_service.py
"""
Servicios de Lógica de Negocio para Clientes

Este archivo contiene la lógica de negocio para:
- Clientes
- Operaciones complejas (crear, actualizar, activar/desactivar)

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from decimal import Decimal

from apps.clientes.models import Cliente


# ============================================================================
# SERVICIO DE CLIENTES
# ============================================================================

class ClienteService:
    """Servicio para manejar la lógica de negocio de Clientes"""
    
    @staticmethod
    @transaction.atomic
    def crear_cliente(nombre, documento, telefono=None, email=None, direccion=None, estado=True):
        """
        Crear un nuevo cliente
        
        Args:
            nombre: Nombre completo del cliente
            documento: Número de documento (único)
            telefono: Teléfono (opcional)
            email: Email (opcional)
            direccion: Dirección (opcional)
            estado: Estado activo/inactivo
        
        Returns:
            Cliente: Instancia del cliente creado
        """
        cliente = Cliente.objects.create(
            nombre=nombre,
            documento=documento,
            telefono=telefono,
            email=email,
            direccion=direccion,
            estado=estado
        )
        
        return cliente
    
    @staticmethod
    @transaction.atomic
    def actualizar_cliente(cliente_id, **kwargs):
        """
        Actualizar un cliente existente
        
        Args:
            cliente_id: ID del cliente a actualizar
            **kwargs: Campos a actualizar
        
        Returns:
            Cliente: Instancia del cliente actualizado
        """
        cliente = Cliente.objects.get(id=cliente_id)
        
        # Actualizar campos proporcionados
        if 'nombre' in kwargs:
            cliente.nombre = kwargs['nombre']
        if 'telefono' in kwargs:
            cliente.telefono = kwargs['telefono']
        if 'email' in kwargs:
            cliente.email = kwargs['email']
        if 'direccion' in kwargs:
            cliente.direccion = kwargs['direccion']
        if 'estado' in kwargs:
            cliente.estado = kwargs['estado']
        
        cliente.save()
        return cliente
    
    @staticmethod
    def activar_cliente(cliente_id):
        """
        Activar un cliente
        
        Args:
            cliente_id: ID del cliente
        
        Returns:
            Cliente: Instancia del cliente activado
        """
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.estado = True
        cliente.save()
        return cliente
    
    @staticmethod
    def desactivar_cliente(cliente_id):
        """
        Desactivar un cliente
        
        Args:
            cliente_id: ID del cliente
        
        Returns:
            Cliente: Instancia del cliente desactivado
        """
        cliente = Cliente.objects.get(id=cliente_id)
        cliente.estado = False
        cliente.save()
        return cliente
    
    @staticmethod
    def obtener_estadisticas_cliente(cliente_id):
        """
        Obtener estadísticas detalladas de un cliente
        
        Args:
            cliente_id: ID del cliente
        
        Returns:
            dict: Estadísticas del cliente
        """
        cliente = Cliente.objects.get(id=cliente_id)
        
        # Verificar si tiene ventas
        if not hasattr(cliente, 'ventas'):
            return {
                'cliente': {
                    'id': cliente.id,
                    'nombre': cliente.nombre,
                    'documento': cliente.documento,
                    'estado': 'ACTIVO' if cliente.estado else 'INACTIVO'
                },
                'ventas': {
                    'total_ventas': 0,
                    'ventas_completadas': 0,
                    'ventas_pendientes': 0,
                    'ventas_canceladas': 0
                },
                'financiero': {
                    'total_comprado': 0,
                    'promedio_compra': 0,
                    'ticket_minimo': 0,
                    'ticket_maximo': 0
                },
                'actividad': {
                    'primera_compra': None,
                    'ultima_compra': None,
                    'dias_desde_ultima_compra': None
                }
            }
        
        # Totales por estado
        total_ventas = cliente.ventas.count()
        ventas_completadas = cliente.ventas.filter(estado='COMPLETADA').count()
        ventas_pendientes = cliente.ventas.filter(estado='PENDIENTE').count()
        ventas_canceladas = cliente.ventas.filter(estado='CANCELADA').count()
        
        # Financiero
        ventas_completadas_qs = cliente.ventas.filter(estado='COMPLETADA')
        total_comprado = ventas_completadas_qs.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        promedio_compra = ventas_completadas_qs.aggregate(
            promedio=Avg('total')
        )['promedio'] or 0
        
        # Ticket mínimo y máximo
        if ventas_completadas > 0:
            ticket_minimo = ventas_completadas_qs.order_by('total').first().total
            ticket_maximo = ventas_completadas_qs.order_by('-total').first().total
        else:
            ticket_minimo = 0
            ticket_maximo = 0
        
        # Actividad
        primera_compra = ventas_completadas_qs.order_by('fecha').first()
        ultima_compra = ventas_completadas_qs.order_by('-fecha').first()
        
        dias_desde_ultima = None
        if ultima_compra:
            dias_desde_ultima = (timezone.now().date() - ultima_compra.fecha.date()).days
        
        estadisticas = {
            'cliente': {
                'id': cliente.id,
                'nombre': cliente.nombre,
                'documento': cliente.documento,
                'email': cliente.email,
                'telefono': cliente.telefono,
                'estado': 'ACTIVO' if cliente.estado else 'INACTIVO',
                'fecha_registro': cliente.fecha_creacion
            },
            'ventas': {
                'total_ventas': total_ventas,
                'ventas_completadas': ventas_completadas,
                'ventas_pendientes': ventas_pendientes,
                'ventas_canceladas': ventas_canceladas
            },
            'financiero': {
                'total_comprado': float(total_comprado),
                'promedio_compra': float(promedio_compra),
                'ticket_minimo': float(ticket_minimo),
                'ticket_maximo': float(ticket_maximo)
            },
            'actividad': {
                'primera_compra': primera_compra.fecha if primera_compra else None,
                'ultima_compra': ultima_compra.fecha if ultima_compra else None,
                'dias_desde_ultima_compra': dias_desde_ultima
            }
        }
        
        return estadisticas
    
    @staticmethod
    def obtener_clientes_frecuentes(limite=10):
        """
        Obtener los clientes más frecuentes
        
        Args:
            limite: Número de clientes a retornar
        
        Returns:
            QuerySet: Clientes ordenados por número de compras
        """
        return Cliente.objects.filter(
            estado=True
        ).annotate(
            total_compras=Count('ventas', filter=Q(ventas__estado='COMPLETADA')),
            total_gastado=Sum('ventas__total', filter=Q(ventas__estado='COMPLETADA'))
        ).filter(
            total_compras__gt=0
        ).order_by('-total_compras')[:limite]
    
    @staticmethod
    def obtener_mejores_clientes(limite=10):
        """
        Obtener los mejores clientes (por monto gastado)
        
        Args:
            limite: Número de clientes a retornar
        
        Returns:
            QuerySet: Clientes ordenados por total gastado
        """
        return Cliente.objects.filter(
            estado=True
        ).annotate(
            total_compras=Count('ventas', filter=Q(ventas__estado='COMPLETADA')),
            total_gastado=Sum('ventas__total', filter=Q(ventas__estado='COMPLETADA'))
        ).filter(
            total_gastado__gt=0
        ).order_by('-total_gastado')[:limite]
    
    @staticmethod
    def obtener_clientes_inactivos(dias=30):
        """
        Obtener clientes que no han comprado en X días
        
        Args:
            dias: Número de días de inactividad
        
        Returns:
            QuerySet: Clientes inactivos
        """
        from datetime import timedelta
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        # Clientes con última compra antes de la fecha límite
        # o sin compras
        clientes_con_compras_antiguas = Cliente.objects.filter(
            estado=True,
            ventas__estado='COMPLETADA',
            ventas__fecha__lt=fecha_limite
        ).annotate(
            ultima_compra=Max('ventas__fecha')
        ).distinct()
        
        # Clientes sin compras
        clientes_sin_compras = Cliente.objects.filter(
            estado=True
        ).annotate(
            total_compras=Count('ventas', filter=Q(ventas__estado='COMPLETADA'))
        ).filter(total_compras=0)
        
        # Combinar ambos
        return (clientes_con_compras_antiguas | clientes_sin_compras).distinct()
    
    @staticmethod
    def buscar_clientes(query):
        """
        Buscar clientes por nombre, documento, email o teléfono
        
        Args:
            query: Texto a buscar
        
        Returns:
            QuerySet: Clientes que coinciden con la búsqueda
        """
        return Cliente.objects.filter(
            Q(nombre__icontains=query) |
            Q(documento__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query)
        )


# Importar Max para la función obtener_clientes_inactivos
from django.db.models import Max