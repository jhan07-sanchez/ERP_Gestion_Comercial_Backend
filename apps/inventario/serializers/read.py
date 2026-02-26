# apps/inventario/serializers/read.py
"""
Serializers de LECTURA para Inventario

Este archivo contiene los serializers para:
- Leer datos (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Separados de los serializers de escritura para:
- Mayor claridad en el código
- Validaciones específicas para cada operación
- Mejor organización
"""

from rest_framework import serializers
from apps.inventario.models import Inventario, MovimientoInventario
from apps.productos.models import Producto
from apps.productos.serializers import ProductoSimpleSerializer


# ============================================================================
# SERIALIZERS DE INVENTARIO (READ)
# ============================================================================

class InventarioReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Inventario

    Usado en:
    - GET /api/inventario/inventarios/ (lista)
    - GET /api/inventario/inventarios/{id}/ (detalle)

    Nota: El inventario es de solo lectura desde la API.
    Se actualiza automáticamente con los movimientos.
    """
    # Información del producto
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_imagen = serializers.ImageField(source='producto.imagen', read_only=True)

    # Información de la categoría
    categoria = serializers.CharField(source='producto.categoria.nombre', read_only=True)
    categoria_id = serializers.IntegerField(source='producto.categoria.id', read_only=True)

    # Precios
    precio_compra = serializers.DecimalField(
        source='producto.precio_compra',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    precio_venta = serializers.DecimalField(
        source='producto.precio_venta',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )

    # Stock
    stock_minimo = serializers.IntegerField(source='producto.stock_minimo', read_only=True)
    estado_stock = serializers.SerializerMethodField()

    # Valores calculados
    valor_compra = serializers.SerializerMethodField()
    valor_venta = serializers.SerializerMethodField()
    ganancia_potencial = serializers.SerializerMethodField()

    class Meta:
        model = Inventario
        fields = [
            'id',
            'producto',
            'producto_codigo',
            'producto_nombre',
            'producto_imagen',
            'categoria',
            'categoria_id',
            'stock_actual',
            'stock_minimo',
            'estado_stock',
            'precio_compra',
            'precio_venta',
            'valor_compra',
            'valor_venta',
            'ganancia_potencial',
            'fecha_actualizacion'
        ]

    def get_estado_stock(self, obj):
        """
        Determinar estado del stock

        Returns:
            dict: Estado con código, texto, color e icono
        """
        if obj.stock_actual == 0:
            return {
                'codigo': 'SIN_STOCK',
                'texto': 'Sin stock disponible',
                'color': 'red',
                'icono': '❌'
            }
        elif obj.stock_actual <= obj.producto.stock_minimo:
            return {
                'codigo': 'BAJO',
                'texto': 'Stock bajo',
                'color': 'orange',
                'icono': '⚠️'
            }
        else:
            return {
                'codigo': 'OK',
                'texto': 'Stock normal',
                'color': 'green',
                'icono': '✓'
            }

    def get_valor_compra(self, obj):
        """Calcular valor total a precio de compra"""
        return float(obj.stock_actual * obj.producto.precio_compra)

    def get_valor_venta(self, obj):
        """Calcular valor total a precio de venta"""
        return float(obj.stock_actual * obj.producto.precio_venta)

    def get_ganancia_potencial(self, obj):
        """Calcular ganancia potencial si se vende todo el stock"""
        compra = obj.stock_actual * obj.producto.precio_compra
        venta = obj.stock_actual * obj.producto.precio_venta
        return float(venta - compra)


# ============================================================================
# SERIALIZERS DE MOVIMIENTO DE INVENTARIO (READ)
# ============================================================================

class MovimientoInventarioReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Movimientos de Inventario

    Usado en:
    - GET /api/inventario/movimientos/ (lista)
    - GET /api/inventario/movimientos/{id}/ (detalle)
    """
    # Información del producto
    producto_codigo = serializers.CharField(source='producto.codigo', read_only=True)
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_info = ProductoSimpleSerializer(source='producto', read_only=True)

    # Información del usuario
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    usuario_email = serializers.EmailField(source='usuario.email', read_only=True)

    # Tipo de movimiento
    tipo_display = serializers.CharField(source='get_tipo_movimiento_display', read_only=True)
    tipo_badge = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoInventario
        fields = [
            'id',
            'producto',
            'producto_codigo',
            'producto_nombre',
            'producto_info',
            'tipo_movimiento',
            'tipo_display',
            'tipo_badge',
            'cantidad',
            'referencia',
            'usuario',
            'usuario_username',
            'usuario_email',
            'fecha'
        ]

    def get_tipo_badge(self, obj):
        """
        Obtener información de badge para mostrar el tipo de movimiento

        Útil para el frontend

        Returns:
            dict: Información de badge con texto, color, icono y clase CSS
        """
        if obj.tipo_movimiento == 'ENTRADA':
            return {
                'texto': 'ENTRADA',
                'color': 'green',
                'icono': '↑',
                'clase': 'badge-success'
            }
        else:  # SALIDA
            return {
                'texto': 'SALIDA',
                'color': 'red',
                'icono': '↓',
                'clase': 'badge-danger'
            }