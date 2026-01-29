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
from apps.inventario.models import (
    Producto,
    Categoria,
    Inventario,
    MovimientoInventario
)


# ============================================================================
# SERIALIZERS DE CATEGORÍA (READ)
# ============================================================================

class CategoriaReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Categorías
    
    Usado en:
    - GET /api/inventario/categorias/ (lista)
    - GET /api/inventario/categorias/{id}/ (detalle)
    
    Incluye:
    - Información completa de la categoría
    - Total de productos en la categoría
    - Total de productos activos
    """
    total_productos = serializers.SerializerMethodField()
    productos_activos = serializers.SerializerMethodField()
    
    class Meta:
        model = Categoria
        fields = [
            'id',
            'nombre',
            'descripcion',
            'total_productos',
            'productos_activos',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_total_productos(self, obj):
        """Obtener total de productos en la categoría"""
        return obj.productos.count()
    
    def get_productos_activos(self, obj):
        """Obtener total de productos activos"""
        return obj.productos.filter(estado=True).count()


class CategoriaSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de categoría para usar en relaciones
    
    Usado en:
    - Campos anidados de otros serializers
    - Respuestas donde no se necesita toda la información
    """
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']


# ============================================================================
# SERIALIZERS DE PRODUCTO (READ)
# ============================================================================

class ProductoListSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para listar productos (vista resumida)
    
    Usado en:
    - GET /api/inventario/productos/ (lista)
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
    - GET /api/inventario/productos/{id}/ (detalle)
    
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