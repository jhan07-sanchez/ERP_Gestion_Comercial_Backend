# apps/productos/serializers/read.py
"""
Serializers de LECTURA para Productos

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
from apps.productos.models import Producto
from apps.categorias.serializers import CategoriaReadSerializer, CategoriaSimpleSerializer
from apps.inventario.models import Inventario


# ============================================================================
# SERIALIZERS DE PRODUCTO (READ)
# ============================================================================

class ProductoListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar productos (vista resumida)

    Usado en:
    - GET /api/productos/ (lista)
    - Relaciones de otros modelos

    Incluye:
    - Información básica del producto
    - Nombre de la categoría
    - Stock actual
    - Estado del stock
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    categoria_info = CategoriaSimpleSerializer(source='categoria', read_only=True)
    stock_actual = serializers.SerializerMethodField()
    estado_stock = serializers.SerializerMethodField()
    margen_ganancia = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'codigo',
            'nombre',
            'categoria',
            'categoria_nombre',
            'categoria_info',
            'precio_compra',
            'precio_venta',
            'margen_ganancia',
            'stock_actual',
            'stock_minimo',
            'estado_stock',
            'estado',
            'imagen'
        ]

    def get_stock_actual(self, obj):
        """
        Obtener stock actual del inventario

        Returns:
            int: Stock actual o 0 si no existe inventario
        """
        try:
            return obj.inventario.stock_actual
        except Inventario.DoesNotExist:
            return 0

    def get_estado_stock(self, obj):
        """
        Obtener estado del stock

        Retorna:
        - SIN_STOCK: stock = 0
        - BAJO: stock <= stock_minimo
        - OK: stock > stock_minimo

        Returns:
            dict: Diccionario con código, texto y color del estado
        """
        try:
            stock = obj.inventario.stock_actual
            if stock == 0:
                return {
                    'codigo': 'SIN_STOCK',
                    'texto': 'Sin stock',
                    'color': 'red',
                    'icono': '❌'
                }
            elif stock <= obj.stock_minimo:
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
        except Inventario.DoesNotExist:
            return {
                'codigo': 'SIN_INVENTARIO',
                'texto': 'Sin inventario',
                'color': 'gray',
                'icono': '⊘'
            }

    def get_margen_ganancia(self, obj):
        """
        Calcular margen de ganancia en porcentaje

        Fórmula: ((precio_venta - precio_compra) / precio_compra) * 100

        Returns:
            float: Margen de ganancia en porcentaje
        """
        if obj.precio_compra > 0:
            margen = ((obj.precio_venta - obj.precio_compra) / obj.precio_compra) * 100
            return round(margen, 2)
        return 0


class ProductoDetailSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para detalle de producto (vista completa)

    Usado en:
    - GET /api/productos/{id}/ (detalle)

    Incluye:
    - Toda la información del producto
    - Información de categoría
    - Stock actual y estado
    - Valor total en inventario
    - Últimos movimientos
    - Estadísticas
    """
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    categoria_info = CategoriaReadSerializer(source='categoria', read_only=True)

    # Stock
    stock_actual = serializers.SerializerMethodField()
    estado_stock = serializers.SerializerMethodField()
    valor_inventario = serializers.SerializerMethodField()

    # Cálculos
    margen_ganancia = serializers.SerializerMethodField()
    margen_ganancia_unitario = serializers.SerializerMethodField()

    # Movimientos
    ultimos_movimientos = serializers.SerializerMethodField()
    total_entradas = serializers.SerializerMethodField()
    total_salidas = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'codigo',
            'nombre',
            'descripcion',
            'categoria',
            'categoria_nombre',
            'categoria_info',
            'precio_compra',
            'precio_venta',
            'margen_ganancia',
            'margen_ganancia_unitario',
            'fecha_ingreso',
            'stock_actual',
            'stock_minimo',
            'estado_stock',
            'valor_inventario',
            'estado',
            'imagen',
            'ultimos_movimientos',
            'total_entradas',
            'total_salidas',
            'fecha_creacion',
            'fecha_actualizacion'
        ]

    def get_stock_actual(self, obj):
        """Obtener stock actual del inventario"""
        try:
            return obj.inventario.stock_actual
        except Inventario.DoesNotExist:
            return 0

    def get_estado_stock(self, obj):
        """
        Obtener estado detallado del stock

        Returns:
            dict: Estado completo con código, mensaje, color, urgencia y datos
        """
        try:
            stock = obj.inventario.stock_actual
            diferencia = stock - obj.stock_minimo

            if stock == 0:
                estado = 'SIN_STOCK'
                mensaje = 'Producto sin stock disponible'
                color = 'red'
                urgencia = 'alta'
            elif stock <= obj.stock_minimo:
                estado = 'BAJO'
                mensaje = f'Stock bajo. Faltan {abs(diferencia)} unidades para el mínimo'
                color = 'orange'
                urgencia = 'media'
            else:
                estado = 'OK'
                mensaje = f'Stock normal. {diferencia} unidades sobre el mínimo'
                color = 'green'
                urgencia = 'baja'

            return {
                'codigo': estado,
                'mensaje': mensaje,
                'color': color,
                'urgencia': urgencia,
                'stock_actual': stock,
                'stock_minimo': obj.stock_minimo,
                'diferencia': diferencia
            }
        except Inventario.DoesNotExist:
            return {
                'codigo': 'SIN_INVENTARIO',
                'mensaje': 'Producto sin registro de inventario',
                'color': 'gray',
                'urgencia': 'alta',
                'stock_actual': 0,
                'stock_minimo': obj.stock_minimo,
                'diferencia': -obj.stock_minimo
            }

    def get_valor_inventario(self, obj):
        """
        Calcular valor total del inventario de este producto

        Fórmula: stock_actual * precio_compra/venta

        Returns:
            dict: Valores a precio de compra, venta y ganancia potencial
        """
        try:
            stock = obj.inventario.stock_actual
            valor_compra = float(stock * obj.precio_compra)
            valor_venta = float(stock * obj.precio_venta)
            ganancia = float(stock * (obj.precio_venta - obj.precio_compra))

            return {
                'compra': valor_compra,
                'venta': valor_venta,
                'ganancia_potencial': ganancia
            }
        except Inventario.DoesNotExist:
            return {
                'compra': 0,
                'venta': 0,
                'ganancia_potencial': 0
            }

    def get_margen_ganancia(self, obj):
        """Calcular margen de ganancia en porcentaje"""
        if obj.precio_compra > 0:
            margen = ((obj.precio_venta - obj.precio_compra) / obj.precio_compra) * 100
            return round(margen, 2)
        return 0

    def get_margen_ganancia_unitario(self, obj):
        """Calcular ganancia por unidad vendida"""
        return float(obj.precio_venta - obj.precio_compra)

    def get_ultimos_movimientos(self, obj):
        """
        Obtener los últimos 10 movimientos del producto

        Returns:
            list: Lista de diccionarios con información de movimientos
        """
        movimientos = obj.movimientos.select_related('usuario').order_by('-fecha')[:10]
        return [{
            'id': mov.id,
            'tipo': mov.tipo_movimiento,
            'tipo_display': mov.get_tipo_movimiento_display(),
            'cantidad': mov.cantidad,
            'referencia': mov.referencia,
            'usuario': mov.usuario.username,
            'fecha': mov.fecha
        } for mov in movimientos]

    def get_total_entradas(self, obj):
        """
        Obtener total de unidades ingresadas

        Returns:
            int: Total de unidades ingresadas
        """
        from django.db.models import Sum
        total = obj.movimientos.filter(
            tipo_movimiento='ENTRADA'
        ).aggregate(total=Sum('cantidad'))['total']
        return total or 0

    def get_total_salidas(self, obj):
        """
        Obtener total de unidades que han salido

        Returns:
            int: Total de unidades que salieron
        """
        from django.db.models import Sum
        total = obj.movimientos.filter(
            tipo_movimiento='SALIDA'
        ).aggregate(total=Sum('cantidad'))['total']
        return total or 0


class ProductoSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de producto para usar en relaciones

    Usado en:
    - Campos anidados de otros serializers (ventas, compras, etc.)
    - Respuestas donde no se necesita toda la información
    """
    stock_actual = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            'id',
            'codigo',
            'nombre',
            'precio_venta',
            'stock_actual'
        ]

    def get_stock_actual(self, obj):
        """Obtener stock actual"""
        try:
            return obj.inventario.stock_actual
        except Inventario.DoesNotExist:
            return 0
