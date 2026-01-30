# apps/clientes/serializers/read.py
"""
Serializers de LECTURA para Clientes

Este archivo contiene los serializers para:
- Leer datos de clientes (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from apps.clientes.models import Cliente


# ============================================================================
# SERIALIZERS DE CLIENTE (READ)
# ============================================================================

class ClienteListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar clientes (vista resumida)
    
    Usado en:
    - GET /api/clientes/ (lista)
    
    Incluye:
    - Información básica del cliente
    - Estado activo/inactivo
    """
    estado_badge = serializers.SerializerMethodField()
    
    class Meta:
        model = Cliente
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
        Obtener badge del estado del cliente
        
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


class ClienteDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para detalle de cliente (vista completa)
    
    Usado en:
    - GET /api/clientes/{id}/ (detalle)
    
    Incluye:
    - Toda la información del cliente
    - Estadísticas de ventas
    - Estado del cliente
    """
    estado_badge = serializers.SerializerMethodField()
    total_ventas = serializers.SerializerMethodField()
    total_comprado = serializers.SerializerMethodField()
    ultima_compra = serializers.SerializerMethodField()
    
    class Meta:
        model = Cliente
        fields = [
            'id',
            'nombre',
            'documento',
            'telefono',
            'email',
            'direccion',
            'estado',
            'estado_badge',
            'total_ventas',
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
    
    def get_total_ventas(self, obj):
        """
        Obtener total de ventas del cliente
        
        Returns:
            int: Número total de ventas
        """
        return obj.ventas.count() if hasattr(obj, 'ventas') else 0
    
    def get_total_comprado(self, obj):
        """
        Obtener total en dinero que ha comprado el cliente
        
        Returns:
            float: Total comprado
        """
        from django.db.models import Sum
        if hasattr(obj, 'ventas'):
            total = obj.ventas.filter(
                estado='COMPLETADA'
            ).aggregate(total=Sum('total'))['total']
            return float(total) if total else 0
        return 0
    
    def get_ultima_compra(self, obj):
        """
        Obtener información de la última compra
        
        Returns:
            dict: Información de la última compra o None
        """
        if hasattr(obj, 'ventas'):
            ultima = obj.ventas.filter(
                estado='COMPLETADA'
            ).order_by('-fecha').first()
            
            if ultima:
                return {
                    'id': ultima.id,
                    'total': float(ultima.total),
                    'fecha': ultima.fecha
                }
        return None


class ClienteSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de cliente para usar en relaciones
    
    Usado en:
    - Relaciones con ventas
    - Respuestas donde no se necesita toda la información
    """
    
    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'documento', 'telefono', 'email']