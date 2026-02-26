# apps/inventario/services/inventario_service.py
"""
Servicios de Lógica de Negocio para Inventario

Este archivo contiene la lógica de negocio para:
- Inventario (stock)
- Movimientos de Inventario

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from apps.productos.models import Producto
from apps.categorias.models import Categoria
from apps.inventario.models import Inventario, MovimientoInventario


# ============================================================================
# SERVICIO DE INVENTARIO
# ============================================================================

class InventarioService:
    """Servicio para manejar la lógica de negocio de Inventario"""

    @staticmethod
    @transaction.atomic
    def ajustar_stock(producto_id, stock_nuevo, usuario, motivo):
        """
        Ajustar el stock manualmente (con precaución)

        Args:
            producto_id: ID del producto
            stock_nuevo: Nuevo valor de stock
            usuario: Usuario que realiza el ajuste
            motivo: Motivo del ajuste

        Returns:
            tuple: (inventario, movimiento)
        """
        producto = Producto.objects.get(id=producto_id)
        inventario, _ = Inventario.objects.get_or_create(producto=producto)

        stock_anterior = inventario.stock_actual
        diferencia = stock_nuevo - stock_anterior

        # Actualizar el inventario
        inventario.stock_actual = stock_nuevo
        inventario.save()

        # Registrar el movimiento
        tipo = 'ENTRADA' if diferencia > 0 else 'SALIDA'
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo_movimiento=tipo,
            cantidad=abs(diferencia),
            referencia=f'AJUSTE: {motivo}',
            usuario=usuario
        )

        return inventario, movimiento

    @staticmethod
    def obtener_estadisticas_generales():
        """
        Obtener estadísticas generales del inventario

        Returns:
            dict: Estadísticas del inventario completo
        """
        inventarios = Inventario.objects.select_related('producto', 'producto__categoria')

        # Stock total
        stock_total = inventarios.aggregate(total=Sum('stock_actual'))['total'] or 0

        # Productos con stock bajo
        productos_stock_bajo = inventarios.filter(
            stock_actual__lte=F('producto__stock_minimo')
        ).count()

        # Productos sin stock
        productos_sin_stock = inventarios.filter(stock_actual=0).count()

        # Valor total del inventario
        valor_compra = sum([
            inv.stock_actual * inv.producto.precio_compra
            for inv in inventarios
        ])

        valor_venta = sum([
            inv.stock_actual * inv.producto.precio_venta
            for inv in inventarios
        ])

        # Por categoría
        categorias = Categoria.objects.annotate(
            total_stock=Sum('productos__inventario__stock_actual'),
            total_productos=Count('productos')
        ).values('nombre', 'total_stock', 'total_productos')

        estadisticas = {
            'resumen': {
                'total_productos': inventarios.count(),
                'stock_total': stock_total,
                'productos_stock_bajo': productos_stock_bajo,
                'productos_sin_stock': productos_sin_stock,
            },
            'valores': {
                'valor_compra': float(valor_compra),
                'valor_venta': float(valor_venta),
                'ganancia_potencial': float(valor_venta - valor_compra)
            },
            'por_categoria': list(categorias),
            'fecha_consulta': timezone.now()
        }

        return estadisticas


# ============================================================================
# SERVICIO DE MOVIMIENTOS
# ============================================================================

class MovimientoInventarioService:
    """Servicio para manejar la lógica de negocio de Movimientos"""

    @staticmethod
    @transaction.atomic
    def registrar_entrada(producto_id, cantidad, referencia, usuario):
        """
        Registrar una entrada de inventario

        Args:
            producto_id: ID del producto
            cantidad: Cantidad a ingresar
            referencia: Referencia del movimiento
            usuario: Usuario que registra

        Returns:
            tuple: (movimiento, inventario)
        """
        producto = Producto.objects.get(id=producto_id)

        # Crear el movimiento
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo_movimiento='ENTRADA',
            cantidad=cantidad,
            referencia=referencia,
            usuario=usuario
        )

        # Actualizar inventario
        inventario, _ = Inventario.objects.get_or_create(producto=producto)
        inventario.stock_actual += cantidad
        inventario.save()

        return movimiento, inventario

    @staticmethod
    @transaction.atomic
    def registrar_salida(producto_id, cantidad, referencia, usuario):
        """
        Registrar una salida de inventario

        Args:
            producto_id: ID del producto
            cantidad: Cantidad a sacar
            referencia: Referencia del movimiento
            usuario: Usuario que registra

        Returns:
            tuple: (movimiento, inventario)

        Raises:
            ValueError: Si no hay stock suficiente
        """
        producto = Producto.objects.get(id=producto_id)

        # Verificar stock disponible
        try:
            inventario = Inventario.objects.get(producto=producto)
        except Inventario.DoesNotExist:
            raise ValueError(
                f'El producto {producto.nombre} no tiene inventario registrado.'
            )

        if inventario.stock_actual < cantidad:
            raise ValueError(
                f'Stock insuficiente. '
                f'Disponible: {inventario.stock_actual}, '
                f'Solicitado: {cantidad}'
            )

        # Crear el movimiento
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo_movimiento='SALIDA',
            cantidad=cantidad,
            referencia=referencia,
            usuario=usuario
        )

        # Actualizar inventario
        inventario.stock_actual -= cantidad
        inventario.save()

        return movimiento, inventario

    @staticmethod
    def obtener_resumen_movimientos(fecha_inicio=None, fecha_fin=None):
        """
        Obtener resumen de movimientos en un período

        Args:
            fecha_inicio: Fecha inicial (opcional)
            fecha_fin: Fecha final (opcional)

        Returns:
            dict: Resumen de movimientos
        """
        queryset = MovimientoInventario.objects.all()

        # Filtrar por fechas
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        # Totales
        total_movimientos = queryset.count()

        entradas = queryset.filter(tipo_movimiento='ENTRADA')
        salidas = queryset.filter(tipo_movimiento='SALIDA')

        total_entradas = entradas.aggregate(total=Sum('cantidad'))['total'] or 0
        total_salidas = salidas.aggregate(total=Sum('cantidad'))['total'] or 0

        resumen = {
            'periodo': {
                'inicio': fecha_inicio,
                'fin': fecha_fin
            },
            'totales': {
                'movimientos': total_movimientos,
                'entradas': entradas.count(),
                'salidas': salidas.count()
            },
            'unidades': {
                'entradas': total_entradas,
                'salidas': total_salidas,
                'diferencia': total_entradas - total_salidas
            },
            'fecha_consulta': timezone.now()
        }

        return resumen