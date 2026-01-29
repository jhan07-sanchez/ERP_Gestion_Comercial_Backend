# apps/inventario/services/inventario_service.py
"""
Servicios de Lógica de Negocio para Inventario

Este archivo contiene la lógica de negocio para:
- Productos
- Categorías
- Inventario
- Movimientos de Inventario

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from apps.inventario.models import (
    Producto,
    Categoria,
    Inventario,
    MovimientoInventario
)


# ============================================================================
# SERVICIO DE CATEGORÍAS
# ============================================================================

class CategoriaService:
    """Servicio para manejar la lógica de negocio de Categorías"""
    
    @staticmethod
    def crear_categoria(nombre, descripcion=None):
        """
        Crear una nueva categoría
        
        Args:
            nombre: Nombre de la categoría
            descripcion: Descripción opcional
        
        Returns:
            Categoria: Instancia de la categoría creada
        """
        categoria = Categoria.objects.create(
            nombre=nombre.strip().title(),
            descripcion=descripcion.strip() if descripcion else None
        )
        return categoria
    
    @staticmethod
    def actualizar_categoria(categoria_id, nombre=None, descripcion=None):
        """
        Actualizar una categoría existente
        
        Args:
            categoria_id: ID de la categoría
            nombre: Nuevo nombre (opcional)
            descripcion: Nueva descripción (opcional)
        
        Returns:
            Categoria: Instancia de la categoría actualizada
        """
        categoria = Categoria.objects.get(id=categoria_id)
        
        if nombre:
            categoria.nombre = nombre.strip().title()
        
        if descripcion is not None:
            categoria.descripcion = descripcion.strip() if descripcion else None
        
        categoria.save()
        return categoria
    
    @staticmethod
    def eliminar_categoria(categoria_id):
        """
        Eliminar una categoría (solo si no tiene productos)
        
        Args:
            categoria_id: ID de la categoría
        
        Raises:
            ValueError: Si la categoría tiene productos asignados
        """
        categoria = Categoria.objects.get(id=categoria_id)
        
        # Verificar que no tenga productos
        total_productos = categoria.productos.count()
        if total_productos > 0:
            raise ValueError(
                f'No se puede eliminar la categoría "{categoria.nombre}" '
                f'porque tiene {total_productos} producto(s) asignado(s).'
            )
        
        categoria.delete()
    
    @staticmethod
    def obtener_estadisticas_categoria(categoria_id):
        """
        Obtener estadísticas de una categoría
        
        Returns:
            dict: Estadísticas de la categoría
        """
        categoria = Categoria.objects.get(id=categoria_id)
        productos = categoria.productos.all()
        
        estadisticas = {
            'id': categoria.id,
            'nombre': categoria.nombre,
            'total_productos': productos.count(),
            'productos_activos': productos.filter(estado=True).count(),
            'productos_inactivos': productos.filter(estado=False).count(),
            'stock_total': sum([
                p.inventario.stock_actual 
                for p in productos 
                if hasattr(p, 'inventario')
            ]),
            'valor_inventario': sum([
                p.inventario.stock_actual * p.precio_compra
                for p in productos
                if hasattr(p, 'inventario')
            ]),
            'productos_stock_bajo': productos.filter(
                inventario__stock_actual__lte=F('stock_minimo')
            ).count() if productos.exists() else 0
        }
        
        return estadisticas


# ============================================================================
# SERVICIO DE PRODUCTOS
# ============================================================================

class ProductoService:
    """Servicio para manejar la lógica de negocio de Productos"""
    
    @staticmethod
    @transaction.atomic
    def crear_producto(codigo, nombre, categoria_id, precio_compra, precio_venta,
                      fecha_ingreso, stock_minimo=0, descripcion=None,
                      estado=True, imagen=None):
        """
        Crear un nuevo producto con su inventario inicial
        
        Args:
            codigo: Código único del producto
            nombre: Nombre del producto
            categoria_id: ID de la categoría
            precio_compra: Precio de compra
            precio_venta: Precio de venta
            fecha_ingreso: Fecha de ingreso al sistema
            stock_minimo: Stock mínimo permitido
            descripcion: Descripción opcional
            estado: Estado activo/inactivo
            imagen: Imagen del producto (opcional)
        
        Returns:
            Producto: Instancia del producto creado
        """
        # Obtener la categoría
        categoria = Categoria.objects.get(id=categoria_id)
        
        # Crear el producto
        producto = Producto.objects.create(
            codigo=codigo.strip().upper(),
            nombre=nombre.strip(),
            categoria=categoria,
            precio_compra=precio_compra,
            precio_venta=precio_venta,
            fecha_ingreso=fecha_ingreso,
            stock_minimo=stock_minimo,
            descripcion=descripcion.strip() if descripcion else None,
            estado=estado,
            imagen=imagen
        )
        
        # Crear inventario inicial en 0
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