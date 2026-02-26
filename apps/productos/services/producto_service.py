# apps/productos/services/producto_service.py
"""
Servicio de Lógica de Negocio para Productos

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, F
from apps.productos.models import Producto
from apps.inventario.models import Inventario


# ============================================================================
# SERVICIO DE PRODUCTOS
# ============================================================================

class ProductoService:
    """Servicio para manejar la lógica de negocio de Productos"""

    @staticmethod
    @transaction.atomic
    def crear_producto(**data):
        """
        Crear un nuevo producto con su inventario inicial

        data proviene directamente de serializer.validated_data
        """

        producto = Producto.objects.create(**data)

        Inventario.objects.create(
            producto=producto,
            stock_actual=0
        )

        return producto

    @staticmethod
    def actualizar_producto(producto_id, **kwargs):
        """
        Actualizar un producto existente

        Args:
            producto_id: ID del producto
            **kwargs: Campos a actualizar

        Returns:
            Producto: Instancia del producto actualizado

        Nota: El código NO se puede actualizar
        """
        producto = Producto.objects.get(id=producto_id)

        # Campos actualizables
        campos_permitidos = [
            'nombre', 'descripcion', 'categoria', 'precio_compra',
            'precio_venta', 'fecha_ingreso', 'stock_minimo', 'estado', 'imagen'
        ]

        for campo, valor in kwargs.items():
            if campo in campos_permitidos and valor is not None:
                if campo == 'nombre' or campo == 'descripcion':
                    valor = valor.strip()
                setattr(producto, campo, valor)

        producto.save()
        return producto

    @staticmethod
    def activar_producto(producto_id):
        """Activar un producto"""
        producto = Producto.objects.get(id=producto_id)
        producto.estado = True
        producto.save()
        return producto

    @staticmethod
    def desactivar_producto(producto_id):
        """Desactivar un producto"""
        producto = Producto.objects.get(id=producto_id)
        producto.estado = False
        producto.save()
        return producto

    @staticmethod
    def obtener_productos_stock_bajo():
        """
        Obtener productos con stock bajo o sin stock

        Returns:
            QuerySet: Productos con stock <= stock_minimo
        """
        return Producto.objects.filter(
            inventario__stock_actual__lte=F('stock_minimo')
        ).select_related('categoria', 'inventario')

    @staticmethod
    def obtener_estadisticas_producto(producto_id):
        """
        Obtener estadísticas detalladas de un producto

        Returns:
            dict: Estadísticas del producto
        """
        producto = Producto.objects.select_related('categoria').get(id=producto_id)

        # Obtener stock actual
        try:
            stock_actual = producto.inventario.stock_actual
        except Inventario.DoesNotExist:
            stock_actual = 0

        # Obtener movimientos
        movimientos = producto.movimientos.all()
        total_entradas = movimientos.filter(
            tipo_movimiento='ENTRADA'
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        total_salidas = movimientos.filter(
            tipo_movimiento='SALIDA'
        ).aggregate(total=Sum('cantidad'))['total'] or 0

        estadisticas = {
            'producto': {
                'id': producto.id,
                'codigo': producto.codigo,
                'nombre': producto.nombre,
                'categoria': producto.categoria.nombre
            },
            'precios': {
                'compra': float(producto.precio_compra),
                'venta': float(producto.precio_venta),
                'margen': float(producto.precio_venta - producto.precio_compra),
                'margen_porcentaje': round(
                    ((producto.precio_venta - producto.precio_compra) /
                     producto.precio_compra * 100), 2
                ) if producto.precio_compra > 0 else 0
            },
            'stock': {
                'actual': stock_actual,
                'minimo': producto.stock_minimo,
                'estado': 'OK' if stock_actual > producto.stock_minimo else 'BAJO'
            },
            'movimientos': {
                'total_entradas': total_entradas,
                'total_salidas': total_salidas,
                'total_movimientos': movimientos.count()
            },
            'valores': {
                'inventario_compra': float(stock_actual * producto.precio_compra),
                'inventario_venta': float(stock_actual * producto.precio_venta),
                'ganancia_potencial': float(
                    stock_actual * (producto.precio_venta - producto.precio_compra)
                )
            }
        }

        return estadisticas
