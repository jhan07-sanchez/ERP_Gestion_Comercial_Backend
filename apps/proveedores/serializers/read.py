# apps/proveedores/serializers/read.py
"""
Serializers de LECTURA para Proveedores

Este archivo contiene los serializers para:
- Leer datos de proveedores (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Autor: Sistema ERP
Fecha: 2026-02-06
"""

from rest_framework import serializers
from apps.proveedores.models import Proveedor


# ============================================================================
# SERIALIZERS DE PROVEEDOR (READ)
# ============================================================================

class ProveedorListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar proveedores (vista resumida)
    
    Usado en:
    - GET /api/proveedores/ (lista)
    
    Incluye:
    - Información básica del proveedor
    - Estado activo/inactivo
    """
    estado_badge = serializers.SerializerMethodField()
    
    class Meta:
        model = Proveedor
        fields = [
            'id',
            'nombre',
            'documento',
            'telefono',
            'email',
            'estado',
            'estado_badge',
            'fecha_creacion'
        ]
    
    def get_estado_badge(self, obj):
        """
        Obtener badge del estado del proveedor
        
        Returns:
            dict: Información de badge con color, texto, icono
        """
        if obj.estado:
            return {
                'texto': 'ACTIVO',
                'color': 'green',
                'icono': '✓',
                'clase': 'badge-success'
            }
        else:
            return {
                'texto': 'INACTIVO',
                'color': 'red',
                'icono': '✗',
                'clase': 'badge-danger'
            }


class ProveedorDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para detalle de proveedor (vista completa)
    
    Usado en:
    - GET /api/proveedores/{id}/ (detalle)
    
    Incluye:
    - Toda la información del proveedor
    - Estadísticas de compras
    - Estado del proveedor
    """
    estado_badge = serializers.SerializerMethodField()
    total_compras = serializers.SerializerMethodField()
    total_comprado = serializers.SerializerMethodField()
    ultima_compra = serializers.SerializerMethodField()
    
    class Meta:
        model = Proveedor
        fields = [
            'id',
            'nombre',
            'documento',
            'telefono',
            'email',
            'direccion',
            'estado',
            'estado_badge',
            'total_compras',
            'total_comprado',
            'ultima_compra',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_estado_badge(self, obj):
        """Obtener badge del estado"""
        if obj.estado:
            return {
                'texto': 'ACTIVO',
                'color': 'green',
                'icono': '✓',
                'clase': 'badge-success'
            }
        else:
            return {
                'texto': 'INACTIVO',
                'color': 'red',
                'icono': '✗',
                'clase': 'badge-danger'
            }
    
    def get_total_compras(self, obj):
        """
        Obtener total de compras del proveedor
        
        Returns:
            int: Número total de compras
        """
        return obj.compras.count() if hasattr(obj, 'compras') else 0
    
    def get_total_comprado(self, obj):
        """
        Obtener total en dinero que se le ha comprado al proveedor
        
        Returns:
            float: Total comprado
        """
        from django.db.models import Sum
        if hasattr(obj, 'compras'):
            total = obj.compras.aggregate(total=Sum('total'))['total']
            return float(total) if total else 0
        return 0
    
    def get_ultima_compra(self, obj):
        """
        Obtener información de la última compra
        
        Returns:
            dict: Información de la última compra o None
        """
        if hasattr(obj, 'compras'):
            ultima = obj.compras.order_by('-fecha').first()
            
            if ultima:
                return {
                    'id': ultima.id,
                    'total': float(ultima.total),
                    'fecha': ultima.fecha
                }
        return None


class ProveedorSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de proveedor para usar en relaciones
    
    Usado en:
    - Relaciones con compras
    - Respuestas donde no se necesita toda la información
    """
    
    class Meta:
        model = Proveedor
        fields = ['id', 'nombre', 'documento', 'telefono', 'email']