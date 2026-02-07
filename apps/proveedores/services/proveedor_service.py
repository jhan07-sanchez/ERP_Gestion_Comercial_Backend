# apps/proveedores/services/proveedor_service.py
"""
Servicios de Lógica de Negocio para Proveedores

Este archivo contiene la lógica de negocio para:
- Proveedores
- Operaciones complejas (crear, actualizar, activar/desactivar)

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, Avg, Q, Max
from django.utils import timezone
from decimal import Decimal

from apps.proveedores.models import Proveedor


# ============================================================================
# SERVICIO DE PROVEEDORES
# ============================================================================

class ProveedorService:
    """Servicio para manejar la lógica de negocio de Proveedores"""
    
    @staticmethod
    @transaction.atomic
    def crear_proveedor(nombre, documento, telefono=None, email=None, direccion=None, activo=True):
        """
        Crear un nuevo proveedor
        
        Args:
            nombre: Nombre completo del proveedor
            documento: Número de documento (único)
            telefono: Teléfono (opcional)
            email: Email (opcional)
            direccion: Dirección (opcional)
            activo: Estado activo/inactivo
        
        Returns:
            Proveedor: Instancia del proveedor creado
        """
        proveedor = Proveedor.objects.create(
            nombre=nombre,
            documento=documento,
            telefono=telefono,
            email=email,
            direccion=direccion,
            activo=activo
        )
        
        return proveedor
    
    @staticmethod
    @transaction.atomic
    def actualizar_proveedor(proveedor_id, **kwargs):
        """
        Actualizar un proveedor existente
        
        Args:
            proveedor_id: ID del proveedor a actualizar
            **kwargs: Campos a actualizar
        
        Returns:
            Proveedor: Instancia del proveedor actualizado
        """
        proveedor = Proveedor.objects.get(id=proveedor_id)
        
        # Actualizar campos proporcionados
        if 'nombre' in kwargs:
            proveedor.nombre = kwargs['nombre']
        if 'telefono' in kwargs:
            proveedor.telefono = kwargs['telefono']
        if 'email' in kwargs:
            proveedor.email = kwargs['email']
        if 'direccion' in kwargs:
            proveedor.direccion = kwargs['direccion']
        if 'activo' in kwargs:
            proveedor.activo = kwargs['activo']
        
        proveedor.save()
        return proveedor
    
    @staticmethod
    def activar_proveedor(proveedor_id):
        """
        Activar un proveedor
        
        Args:
            proveedor_id: ID del proveedor
        
        Returns:
            Proveedor: Instancia del proveedor activado
        """
        proveedor = Proveedor.objects.get(id=proveedor_id)
        proveedor.activo = True
        proveedor.save()
        return proveedor
    
    @staticmethod
    def desactivar_proveedor(proveedor_id):
        """
        Desactivar un proveedor
        
        Args:
            proveedor_id: ID del proveedor
        
        Returns:
            Proveedor: Instancia del proveedor desactivado
        """
        proveedor = Proveedor.objects.get(id=proveedor_id)
        proveedor.activo = False
        proveedor.save()
        return proveedor
    
    @staticmethod
    def obtener_estadisticas_proveedor(proveedor_id):
        """
        Obtener estadísticas detalladas de un proveedor
        
        Args:
            proveedor_id: ID del proveedor
        
        Returns:
            dict: Estadísticas del proveedor
        """
        proveedor = Proveedor.objects.get(id=proveedor_id)
        
        # Verificar si tiene compras
        if not hasattr(proveedor, 'compras'):
            return {
                'proveedor': {
                    'id': proveedor.id,
                    'nombre': proveedor.nombre,
                    'documento': proveedor.documento,
                    'estado': 'ACTIVO' if proveedor.activo else 'INACTIVO'
                },
                'compras': {
                    'total_compras': 0,
                },
                'financiero': {
                    'total_comprado': 0,
                    'promedio_compra': 0,
                    'compra_minima': 0,
                    'compra_maxima': 0
                },
                'actividad': {
                    'primera_compra': None,
                    'ultima_compra': None,
                    'dias_desde_ultima_compra': None
                }
            }
        
        # Totales
        total_compras = proveedor.compras.count()
        
        # Financiero
        compras_qs = proveedor.compras.all()
        total_comprado = compras_qs.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        promedio_compra = compras_qs.aggregate(
            promedio=Avg('total')
        )['promedio'] or 0
        
        # Compra mínima y máxima
        if total_compras > 0:
            compra_minima = compras_qs.order_by('total').first().total
            compra_maxima = compras_qs.order_by('-total').first().total
        else:
            compra_minima = 0
            compra_maxima = 0
        
        # Actividad
        primera_compra = compras_qs.order_by('fecha').first()
        ultima_compra = compras_qs.order_by('-fecha').first()
        
        dias_desde_ultima = None
        if ultima_compra:
            dias_desde_ultima = (timezone.now().date() - ultima_compra.fecha).days
        
        estadisticas = {
            'proveedor': {
                'id': proveedor.id,
                'nombre': proveedor.nombre,
                'documento': proveedor.documento,
                'email': proveedor.email,
                'telefono': proveedor.telefono,
                'estado': 'ACTIVO' if proveedor.activo else 'INACTIVO',
                'fecha_registro': proveedor.fecha_creacion
            },
            'compras': {
                'total_compras': total_compras,
            },
            'financiero': {
                'total_comprado': float(total_comprado),
                'promedio_compra': float(promedio_compra),
                'compra_minima': float(compra_minima),
                'compra_maxima': float(compra_maxima)
            },
            'actividad': {
                'primera_compra': primera_compra.fecha if primera_compra else None,
                'ultima_compra': ultima_compra.fecha if ultima_compra else None,
                'dias_desde_ultima_compra': dias_desde_ultima
            }
        }
        
        return estadisticas
    
    @staticmethod
    def obtener_proveedores_frecuentes(limite=10):
        """
        Obtener los proveedores más frecuentes
        
        Args:
            limite: Número de proveedores a retornar
        
        Returns:
            QuerySet: Proveedores ordenados por número de compras
        """
        return Proveedor.objects.filter(
            activo=True
        ).annotate(
            total_compras=Count('compras'),
            total_comprado=Sum('compras__total')
        ).filter(
            total_compras__gt=0
        ).order_by('-total_compras')[:limite]
    
    @staticmethod
    def obtener_mejores_proveedores(limite=10):
        """
        Obtener los mejores proveedores (por monto comprado)
        
        Args:
            limite: Número de proveedores a retornar
        
        Returns:
            QuerySet: Proveedores ordenados por total comprado
        """
        return Proveedor.objects.filter(
            activo=True
        ).annotate(
            total_compras=Count('compras'),
            total_comprado=Sum('compras__total')
        ).filter(
            total_comprado__gt=0
        ).order_by('-total_comprado')[:limite]
    
    @staticmethod
    def obtener_proveedores_inactivos(dias=30):
        """
        Obtener proveedores que no se les ha comprado en X días
        
        Args:
            dias: Número de días de inactividad
        
        Returns:
            QuerySet: Proveedores inactivos
        """
        from datetime import timedelta
        fecha_limite = timezone.now() - timedelta(days=dias)
        
        # Proveedores con última compra antes de la fecha límite
        proveedores_con_compras_antiguas = Proveedor.objects.filter(
            activo=True,
            compras__fecha__lt=fecha_limite
        ).annotate(
            ultima_compra=Max('compras__fecha')
        ).distinct()
        
        # Proveedores sin compras
        proveedores_sin_compras = Proveedor.objects.filter(
            activo=True
        ).annotate(
            total_compras=Count('compras')
        ).filter(total_compras=0)
        
        # Combinar ambos
        return (proveedores_con_compras_antiguas | proveedores_sin_compras).distinct()
    
    @staticmethod
    def buscar_proveedores(query):
        """
        Buscar proveedores por nombre, documento, email o teléfono
        
        Args:
            query: Texto a buscar
        
        Returns:
            QuerySet: Proveedores que coinciden con la búsqueda
        """
        return Proveedor.objects.filter(
            Q(nombre__icontains=query) |
            Q(documento__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query)
        )