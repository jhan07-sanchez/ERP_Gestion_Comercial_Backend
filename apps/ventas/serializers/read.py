# apps/ventas/serializers/read.py
"""
Serializers de LECTURA para Ventas

Este archivo contiene los serializers para:
- Leer datos de ventas (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from apps.ventas.models import Venta, DetalleVenta
from apps.clientes.models import Cliente
from apps.inventario.models import Producto


# ============================================================================
# SERIALIZERS SIMPLES (para relaciones)
# ============================================================================

class ClienteSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple de cliente para usar en relaciones"""

    class Meta:
        model = Cliente
        fields = ['id', 'nombre', 'documento', 'telefono', 'email']


class ProductoSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple de producto para usar en detalles de venta"""
    stock_actual = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = ['id', 'codigo', 'nombre', 'precio_venta', 'stock_actual']

    def get_stock_actual(self, obj):
        """Obtener stock actual del producto"""
        try:
            return obj.inventario.stock_actual
        except:
            return 0


# ============================================================================
# SERIALIZERS DE DETALLE DE VENTA (READ)
# ============================================================================

class DetalleVentaReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Detalle de Venta

    Usado en:
    - Mostrar los productos de una venta
    - Incluye información del producto
    """
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_info = ProductoSimpleSerializer(source='producto', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            'id',
            'producto',
            'producto_codigo',
            'producto_nombre',
            'producto_info',
            'cantidad',
            'precio_unitario',
            'subtotal'
        ]


# ============================================================================
# SERIALIZERS DE VENTA (READ)
# ============================================================================

class VentaListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar ventas (vista resumida)

    Usado en:
    - GET /api/ventas/ (lista)

    Incluye:
    - Información básica de la venta
    - Nombre del cliente
    - Nombre del usuario
    - Estado con badge
    """
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_documento = serializers.CharField(source='cliente.documento', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    estado_badge = serializers.SerializerMethodField()
    total_productos = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = [
            'id',
            'cliente',
            'cliente_nombre',
            'cliente_documento',
            'usuario',
            'usuario_nombre',
            'total',
            'estado',
            'estado_badge',
            'total_productos',
            'fecha'
        ]

    def get_estado_badge(self, obj):
        """
        Obtener información de badge para el estado

        Returns:
            dict: Información de badge con color, texto, icono
        """
        estados = {
            'PENDIENTE': {
                'texto': 'PENDIENTE',
                'color': 'orange',
                'icono': '⏳',
                'clase': 'badge-warning'
            },
            'COMPLETADA': {
                'texto': 'COMPLETADA',
                'color': 'green',
                'icono': '✓',
                'clase': 'badge-success'
            },
            'CANCELADA': {
                'texto': 'CANCELADA',
                'color': 'red',
                'icono': '✗',
                'clase': 'badge-danger'
            }
        }

        return estados.get(obj.estado, {
            'texto': obj.estado,
            'color': 'gray',
            'icono': '?',
            'clase': 'badge-secondary'
        })

    def get_total_productos(self, obj):
        """Obtener total de productos diferentes en la venta"""
        return obj.detalles.count()


class VentaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para detalle de venta (vista completa)

    Usado en:
    - GET /api/ventas/{id}/ (detalle)

    Incluye:
    - Toda la información de la venta
    - Información completa del cliente
    - Información del usuario
    - Detalles de productos vendidos
    - Estadísticas
    """
    # Cliente
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    cliente_info = ClienteSimpleSerializer(source='cliente', read_only=True)

    # Usuario
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)

    # Estado
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    estado_badge = serializers.SerializerMethodField()

    # Detalles
    detalles = DetalleVentaReadSerializer(many=True, read_only=True)

    # Estadísticas
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()

    class Meta:
        model = Venta
        fields = [
            'id',
            'cliente',
            'cliente_nombre',
            'cliente_info',
            'usuario',
            'usuario_nombre',
            'usuario_email',
            'total',
            'estado',
            'estado_display',
            'estado_badge',
            'detalles',
            'total_productos',
            'total_unidades',
            'fecha'
        ]

    def get_estado_badge(self, obj):
        """Obtener badge del estado"""
        estados = {
            'PENDIENTE': {
                'texto': 'PENDIENTE',
                'color': 'orange',
                'icono': '⏳',
                'clase': 'badge-warning'
            },
            'COMPLETADA': {
                'texto': 'COMPLETADA',
                'color': 'green',
                'icono': '✓',
                'clase': 'badge-success'
            },
            'CANCELADA': {
                'texto': 'CANCELADA',
                'color': 'red',
                'icono': '✗',
                'clase': 'badge-danger'
            }
        }

        return estados.get(obj.estado, {
            'texto': obj.estado,
            'color': 'gray',
            'icono': '?',
            'clase': 'badge-secondary'
        })

    def get_total_productos(self, obj):
        """Obtener total de productos diferentes"""
        return obj.detalles.count()

    def get_total_unidades(self, obj):
        """Obtener total de unidades vendidas"""
        from django.db.models import Sum
        total = obj.detalles.aggregate(total=Sum('cantidad'))['total']
        return total or 0


class VentaSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de venta para usar en relaciones

    Usado en:
    - Reportes
    - Relaciones con otras entidades
    """
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = ['id', 'cliente_nombre', 'total', 'estado', 'fecha']