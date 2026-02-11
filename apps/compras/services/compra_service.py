# apps/compras/services/compra_service.py
"""
Servicios de Lógica de Negocio para Compras

Este archivo contiene la lógica de negocio para:
- Compras
- Detalles de Compra
- Operaciones complejas (crear, anular)

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from decimal import Decimal

from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto, Inventario, MovimientoInventario
from apps.proveedores.models import Proveedor


# ============================================================================
# SERVICIO DE COMPRAS
# ============================================================================

class CompraService:
    """Servicio para manejar la lógica de negocio de Compras"""
    
    @staticmethod
    @transaction.atomic
    def crear_compra(proveedor, detalles, usuario, fecha, estado='PENDIENTE'):
        """
        Crear una nueva compra con sus detalles
        
        Args:
            proveedor_id: ID del proveedor
            detalles: Lista de diccionarios con producto_id, cantidad, precio_compra
            usuario: Usuario que crea la compra
            fecha: Fecha de la compra (opcional, por defecto hoy)
            estado: Estado inicial ('PENDIENTE', 'ANULADA', 'REALIZADA')
        
        Returns:
            Compra: Instancia de la compra creada
        
        Proceso:
            1. Obtener el proveedor
            2. Crear la compra
            3. Crear detalles
            4. Actualizar inventario (aumentar stock)
            5. Registrar movimientos
        """
        # 1. Calcular el total
        total = Decimal('0.00')
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            precio = detalle.get('precio_compra', producto.precio_compra)
            cantidad = detalle['cantidad']
            total += Decimal(str(precio)) * Decimal(str(cantidad))
        
        # 2. Crear la compra
        compra = Compra.objects.create(
            proveedor=proveedor,
            usuario=usuario,
            total=total,
            fecha=fecha,
            estado=estado
        )
        
        # 3. Crear detalles y actualizar inventario
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            precio = detalle.get('precio_compra', producto.precio_compra)
            cantidad = detalle['cantidad']
            subtotal = Decimal(str(precio)) * Decimal(str(cantidad))
            
            # Crear detalle
            DetalleCompra.objects.create(
                compra=compra,
                producto=producto,
                cantidad=cantidad,
                precio_compra=precio,
                subtotal=subtotal
            )
            
            # Aumentar inventario
            inventario, created = Inventario.objects.get_or_create(
                producto=producto,
                defaults={'stock_actual': 0}
            )
            inventario.stock_actual += cantidad
            inventario.save()
            
            # Registrar movimiento de inventario
            MovimientoInventario.objects.create(
                producto=producto,
                tipo_movimiento='ENTRADA',
                cantidad=cantidad,
                referencia=f'COMPRA-{compra.id}',
                usuario=usuario
            )
        
        return compra
    
    @staticmethod
    @transaction.atomic
    def anular_compra(compra_id, usuario, motivo):
        """
        Anular una compra
        
        Args:
            compra_id: ID de la compra
            usuario: Usuario que anula la compra
            motivo: Motivo de la anulación
        
        Returns:
            Compra: Instancia de la compra anulada
        
        Proceso:
            1. Validar que se pueda anular
            2. Reducir stock
            3. Registrar movimientos de anulación
            4. Eliminar la compra (o marcarla como anulada si tienes ese campo)
        
        Nota: En este caso eliminamos la compra, pero podrías agregar
        un campo 'estado' al modelo Compra y solo cambiar el estado.
        """
        compra = Compra.objects.select_related('usuario').prefetch_related(
            'detalles__producto'
        ).get(id=compra_id)
        
        # Reducir stock y registrar movimientos
        for detalle in compra.detalles.all():
            # Reducir del inventario
            inventario = Inventario.objects.get(producto=detalle.producto)
            
            # Verificar que haya suficiente stock para anular
            if inventario.stock_actual < detalle.cantidad:
                raise ValueError(
                    f'No hay suficiente stock del producto {detalle.producto.nombre} '
                    f'para anular esta compra. Stock actual: {inventario.stock_actual}, '
                    f'Requerido: {detalle.cantidad}'
                )
            
            inventario.stock_actual -= detalle.cantidad
            inventario.save()
            
            # Registrar movimiento de salida (anulación)
            MovimientoInventario.objects.create(
                producto=detalle.producto,
                tipo_movimiento='SALIDA',
                cantidad=detalle.cantidad,
                referencia=f'ANULACIÓN COMPRA-{compra.id}: {motivo}',
                usuario=usuario
            )
        
        # Eliminar la compra
        # (Si quieres mantener el registro, agrega un campo 'anulada' al modelo)
        compra.estado = 'ANULADA'
        compra.save()
    
        return compra
    
    @staticmethod
    @transaction.atomic
    def marcar_como_realizada(compra_id, usuario):
        compra = Compra.objects.get(id=compra_id)
        if compra.estado != 'PENDIENTE':
                raise ValueError("Solo se pueden marcar como realizadas las compras pendientes.")
        compra.estado = 'REALIZADA'
        compra.save()
        return compra

    
    @staticmethod
    def obtener_estadisticas_compra(compra_id):
        """
        Obtener estadísticas de una compra específica
        
        Returns:
            dict: Estadísticas de la compra
        """
        compra = Compra.objects.select_related('usuario').prefetch_related(
            'detalles__producto'
        ).get(id=compra_id)
        
        # Calcular estadísticas
        total_productos = compra.detalles.count()
        total_unidades = compra.detalles.aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        # Calcular margen potencial
        valor_compra = float(compra.total)
        valor_venta_potencial = 0
        
        for detalle in compra.detalles.all():
            valor_venta_potencial += float(
                detalle.producto.precio_venta * detalle.cantidad
            )
        
        ganancia_potencial = valor_venta_potencial - valor_compra
        margen_porcentaje = 0
        if valor_compra > 0:
            margen_porcentaje = (ganancia_potencial / valor_compra) * 100
        
        estadisticas = {
            'compra': {
                'id': compra.id,
                'total': valor_compra,
                'fecha': compra.fecha
            },
            'proveedor': {
                'nombre': compra.proveedor
            },
            'usuario': {
                'id': compra.usuario.id,
                'username': compra.usuario.username
            },
            'productos': {
                'total_productos': total_productos,
                'total_unidades': total_unidades
            },
            'financiero': {
                'valor_compra': valor_compra,
                'valor_venta_potencial': valor_venta_potencial,
                'ganancia_potencial': ganancia_potencial,
                'margen_porcentaje': round(margen_porcentaje, 2)
            }
        }
        
        return estadisticas
    
    @staticmethod
    def obtener_estadisticas_generales(fecha_inicio=None, fecha_fin=None):
        """
        Obtener estadísticas generales de compras
        
        Args:
            fecha_inicio: Fecha inicial (opcional)
            fecha_fin: Fecha final (opcional)
        
        Returns:
            dict: Estadísticas generales
        """
        queryset = Compra.objects.all()
        
        # Filtrar por fechas
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Totales
        total_compras = queryset.count()
        
        # Totales monetarios
        total_invertido = queryset.aggregate(
            total=Sum('total')
        )['total'] or 0
        
        # Promedio
        promedio_compra = queryset.aggregate(
            promedio=Avg('total')
        )['promedio'] or 0
        
        # Top proveedores
        top_proveedores = queryset.values('proveedor__nombre', 'proveedor__id').annotate(
            total_compras=Count('id'),
            total_invertido=Sum('total')
        ).order_by('-total_invertido')[:5]
        
        estadisticas = {
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'totales': {
                'total_compras': total_compras,
                'total_invertido': float(total_invertido),
                'promedio_compra': float(promedio_compra)
            },
            'top_proveedores': list(top_proveedores),
            'fecha_consulta': timezone.now()
        }
        
        return estadisticas
    
    @staticmethod
    def obtener_compras_por_proveedor(proveedor_id):
        """
        Obtener todas las compras de un proveedor específico

        Args:
            proveedor_id: ID del proveedor

        Returns:
            QuerySet: Compras del proveedor
        """
        return Compra.objects.filter(
        proveedor_id=proveedor_id
        ).select_related('usuario', 'proveedor').prefetch_related('detalles')