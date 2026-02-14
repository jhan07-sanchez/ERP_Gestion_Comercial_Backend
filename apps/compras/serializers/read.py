# apps/compras/serializers/read.py
"""
Serializers de LECTURA para Compras

Este archivo contiene los serializers para:
- Leer datos de compras (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto
from apps.proveedores.serializers import ProveedorSimpleSerializer


# ============================================================================
# SERIALIZERS SIMPLES (para relaciones)
# ============================================================================

class ProductoSimpleSerializer(serializers.ModelSerializer):
    """Serializer simple de producto para usar en detalles de compra"""
    stock_actual = serializers.SerializerMethodField()
    
    class Meta:
        model = Producto
        fields = ['id', 'codigo', 'nombre', 'precio_compra', 'stock_actual']
    
    def get_stock_actual(self, obj):
        """Obtener stock actual del producto"""
        try:
            return obj.inventario.stock_actual
        except:
            return 0


# ============================================================================
# SERIALIZERS DE DETALLE DE COMPRA (READ)
# ============================================================================

class DetalleCompraReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Detalle de Compra
    
    Usado en:
    - Mostrar los productos de una compra
    - Incluye información del producto
    """
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_info = ProductoSimpleSerializer(source='producto', read_only=True)
    margen_potencial = serializers.SerializerMethodField()
    
    class Meta:
        model = DetalleCompra
        fields = [
            'id',
            'producto',
            'producto_codigo',
            'producto_nombre',
            'producto_info',
            'cantidad',
            'precio_compra',
            'subtotal',
            'margen_potencial'
        ]
    
    def get_margen_potencial(self, obj):
        """
        Calcular margen de ganancia potencial si se vende a precio actual
        
        Returns:
            dict: Margen en pesos y porcentaje
        """
        precio_venta = obj.producto.precio_venta
        ganancia_unitaria = precio_venta - obj.precio_compra
        ganancia_total = ganancia_unitaria * obj.cantidad
        
        margen_porcentaje = 0
        if obj.precio_compra > 0:
            margen_porcentaje = ((precio_venta - obj.precio_compra) / obj.precio_compra) * 100
        
        return {
            'ganancia_unitaria': float(ganancia_unitaria),
            'ganancia_total': float(ganancia_total),
            'margen_porcentaje': round(margen_porcentaje, 2)
        }


# ============================================================================
# SERIALIZERS DE COMPRA (READ)
# ============================================================================

class CompraListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar compras (vista resumida)
    
    Usado en:
    - GET /api/compras/ (lista)
    
    Incluye:
    - Información básica de la compra
    - Nombre del proveedor
    - Nombre del usuario
    - Total de productos
    """

    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    proveedor_documento = serializers.CharField(source='proveedor.documento', read_only=True)
    proveedor_info = ProveedorSimpleSerializer(source='proveedor', read_only=True)
    
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()
    estado = serializers.CharField(read_only=True) 
    class Meta:
        model = Compra
        fields = [
            'id',
            'proveedor',
            'proveedor_nombre',         # NUEVO
            'proveedor_documento',      # NUEVO
            'proveedor_info',
            'usuario',
            'usuario_nombre',
            'total',
            'total_productos',
            'total_unidades',
            'fecha',
            'estado'                    # NUEVO
        ]
    
    def get_total_productos(self, obj):
        """Obtener total de productos diferentes en la compra"""
        return obj.detalles.count()
    
    def get_total_unidades(self, obj):
        """Obtener total de unidades compradas"""
        from django.db.models import Sum
        total = obj.detalles.aggregate(total=Sum('cantidad'))['total']
        return total or 0


class CompraDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para detalle de compra (vista completa)
    
    Usado en:
    - GET /api/compras/{id}/ (detalle)
    
    Incluye:
    - Toda la información de la compra
    - Información del usuario
    - Detalles de productos comprados
    - Estadísticas y márgenes
    """
    # Proveedor
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    proveedor_info = ProveedorSimpleSerializer(source='proveedor', read_only=True)

    # Usuario
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)
    
    # Detalles
    detalles = DetalleCompraReadSerializer(many=True, read_only=True)
    
    # Estadísticas
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()
    margen_potencial = serializers.SerializerMethodField()
    
    #motivo de anulacion (si existe)
    motivo_anulacion = serializers.CharField(read_only=True)

    #Estado de la compra (pendiente, anulada, realizada)
    estado = serializers.CharField(read_only=True)
    class Meta:
        model = Compra
        fields = [
            'id',
            'proveedor',
            'proveedor_nombre',        # NUEVO
            'proveedor_info',          # NUEVO
            'usuario',
            'usuario_nombre',
            'usuario_email',
            'total',
            'detalles',
            'total_productos',
            'total_unidades',
            'margen_potencial',
            'fecha',
            'estado',                   # NUEVO
            'motivo_anulacion'           # NUEVO
        ]
    
    def get_total_productos(self, obj):
        """Obtener total de productos diferentes"""
        return obj.detalles.count()
    
    def get_total_unidades(self, obj):
        """Obtener total de unidades compradas"""
        from django.db.models import Sum
        total = obj.detalles.aggregate(total=Sum('cantidad'))['total']
        return total or 0
    
    def get_margen_potencial(self, obj):
        """
        Calcular margen de ganancia potencial total
        
        Compara precio de compra vs precio de venta actual
        """
        ganancia_total = 0
        valor_compra = 0
        valor_venta_potencial = 0
        
        for detalle in obj.detalles.all():
            valor_compra += float(detalle.subtotal)
            valor_venta_potencial += float(
                detalle.producto.precio_venta * detalle.cantidad
            )
        
        ganancia_total = valor_venta_potencial - valor_compra
        
        margen_porcentaje = 0
        if valor_compra > 0:
            margen_porcentaje = (ganancia_total / valor_compra) * 100
        
        return {
            'valor_compra': valor_compra,
            'valor_venta_potencial': valor_venta_potencial,
            'ganancia_potencial': ganancia_total,
            'margen_porcentaje': round(margen_porcentaje, 2)
        }


class CompraSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de compra para usar en relaciones
    
    Usado en:
    - Reportes
    - Relaciones con otras entidades
    """
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    estado = serializers.CharField(read_only=True) 
    class Meta:
        model = Compra
        fields = ['id', 'proveedor', 'proveedor_nombre', 'total', 'fecha', 'estado']