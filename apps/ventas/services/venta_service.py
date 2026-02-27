# apps/ventas/services/venta_service.py
"""
Servicios de Lógica de Negocio para Ventas

Este archivo contiene la lógica de negocio para:
- Ventas
- Detalles de Venta
- Operaciones complejas (crear, cancelar, completar)

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db import transaction
from django.db.models import Sum, Count, F, Q, Avg
from django.utils import timezone
from decimal import Decimal

from apps.ventas.models import Venta, DetalleVenta, PagoVenta
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.inventario.models import Inventario, MovimientoInventario


# ============================================================================
# SERVICIO DE VENTAS
# ============================================================================

class VentaService:
    """Servicio para manejar la lógica de negocio de Ventas"""
    
    @staticmethod
    @transaction.atomic
    def crear_venta(cliente_id, detalles, usuario, estado='PENDIENTE'):
        """
        Crear una nueva venta con sus detalles (Sin pago inmediato)
        
        Args:
            cliente_id: ID del cliente
            detalles: Lista de diccionarios con producto_id, cantidad, precio_unitario
            usuario: Usuario que crea la venta
            estado: Estado inicial de la venta (generalmente PENDIENTE)
        
        Returns:
            Venta: Instancia de la venta creada
        
        Proceso:
            1. Validar cliente
            2. Crear la venta
            3. Crear detalles
            (El inventario NO se descuenta aquí, se descuenta al pagar)
        """
        # 1. Obtener el cliente
        cliente = Cliente.objects.get(id=cliente_id)
        
        # 2. Calcular el total
        total = Decimal('0.00')
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            precio = detalle.get('precio_unitario', producto.precio_venta)
            cantidad = detalle['cantidad']
            total += Decimal(str(precio)) * Decimal(str(cantidad))
        
        # 3. Crear la venta
        venta = Venta.objects.create(
            cliente=cliente,
            usuario=usuario,
            total=total,
            estado=estado
        )
        
        # 4. Crear detalles
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            precio = detalle.get('precio_unitario', producto.precio_venta)
            cantidad = detalle['cantidad']
            subtotal = Decimal(str(precio)) * Decimal(str(cantidad))
            
            # Crear detalle
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=subtotal
            )
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def registrar_pago(venta_id, monto, metodo_pago, usuario, monto_recibido=0, vuelto=0, referencia=None):
        """
        Registra un pago parcial o total para una venta.
        Actualiza el estado de la venta y descuenta el inventario si es el primer pago.
        
        Returns:
            PagoVenta: Instancia del pago creado.
        """
        venta = Venta.objects.prefetch_related('detalles__producto').get(id=venta_id)
        
        if venta.estado == 'CANCELADA':
            raise ValueError('No se pueden registrar pagos a una venta cancelada.')
            
        pagos_previos = venta.pagos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        saldo_pendiente = venta.total - Decimal(str(pagos_previos))
        monto_decimal = Decimal(str(monto))
        
        if monto_decimal <= 0:
            raise ValueError('El monto debe ser mayor a 0.')
            
        if monto_decimal > saldo_pendiente:
            raise ValueError(f'El monto excede el saldo pendiente. Saldo actual: {saldo_pendiente}')
            
        # 1. Registrar el pago
        pago = PagoVenta.objects.create(
            venta=venta,
            monto=monto_decimal,
            metodo_pago=metodo_pago,
            monto_recibido=monto_recibido,
            vuelto=vuelto,
            referencia=referencia,
            usuario=usuario
        )
        
        # 2. Verificar y descontar inventario si es el PRIMER pago (venta pasa de PENDIENTE a PARCIAL o COMPLETADA)
        # O si el método de pago es CRÉDITO (entrega inmediata)
        if venta.estado == 'PENDIENTE':
            for detalle in venta.detalles.all():
                inventario = Inventario.objects.get(producto=detalle.producto)
                inventario.stock_actual -= detalle.cantidad
                inventario.save()
                
                MovimientoInventario.objects.create(
                    producto=detalle.producto,
                    tipo_movimiento='SALIDA',
                    cantidad=detalle.cantidad,
                    referencia=f'VENTA-{venta.id} (Primer Pago)',
                    usuario=usuario
                )
        
        # 3. Recalcular y actualizar estado de la venta
        nuevo_total_pagado = pagos_previos + monto_decimal
        
        if nuevo_total_pagado >= venta.total:
            venta.estado = 'COMPLETADA'
        else:
            venta.estado = 'PARCIAL'
            
        venta.save()
        
        return pago
    
    @staticmethod
    @transaction.atomic
    def completar_venta(venta_id, usuario, notas=None):
        """
        Completar una venta pendiente
        
        Args:
            venta_id: ID de la venta
            usuario: Usuario que completa la venta
            notas: Notas opcionales
        
        Returns:
            Venta: Instancia de la venta completada
        
        Proceso:
            1. Validar que la venta esté pendiente
            2. Reducir inventario
            3. Registrar movimientos
            4. Cambiar estado a COMPLETADA
        """
        venta = Venta.objects.select_related('cliente').prefetch_related(
            'detalles__producto'
        ).get(id=venta_id)
        
        # Validar que esté pendiente
        if venta.estado != 'PENDIENTE':
            raise ValueError(
                f'La venta debe estar en estado PENDIENTE. '
                f'Estado actual: {venta.estado}'
            )
        
        # Reducir inventario y registrar movimientos
        for detalle in venta.detalles.all():
            # Actualizar inventario
            inventario = Inventario.objects.get(producto=detalle.producto)
            inventario.stock_actual -= detalle.cantidad
            inventario.save()
            
            # Registrar movimiento
            MovimientoInventario.objects.create(
                producto=detalle.producto,
                tipo_movimiento='SALIDA',
                cantidad=detalle.cantidad,
                referencia=f'VENTA-{venta.id}',
                usuario=usuario
            )
        
        # Cambiar estado
        venta.estado = 'COMPLETADA'
        venta.save()
        
        return venta
    
    @staticmethod
    @transaction.atomic
    def cancelar_venta(venta_id, usuario, motivo):
        """
        Cancelar una venta
        
        Args:
            venta_id: ID de la venta
            usuario: Usuario que cancela la venta
            motivo: Motivo de la cancelación
        
        Returns:
            Venta: Instancia de la venta cancelada
        
        Proceso:
            1. Validar que se pueda cancelar
            2. Si estaba completada, devolver stock
            3. Registrar movimientos de devolución
            4. Cambiar estado a CANCELADA
        """
        venta = Venta.objects.select_related('cliente').prefetch_related(
            'detalles__producto'
        ).get(id=venta_id)
        
        # Validar que no esté ya cancelada
        if venta.estado == 'CANCELADA':
            raise ValueError('La venta ya está cancelada.')
        
        # Si estaba completada, devolver stock
        if venta.estado == 'COMPLETADA':
            for detalle in venta.detalles.all():
                # Devolver al inventario
                inventario = Inventario.objects.get(producto=detalle.producto)
                inventario.stock_actual += detalle.cantidad
                inventario.save()
                
                # Registrar movimiento de entrada (devolución)
                MovimientoInventario.objects.create(
                    producto=detalle.producto,
                    tipo_movimiento='ENTRADA',
                    cantidad=detalle.cantidad,
                    referencia=f'CANCELACIÓN VENTA-{venta.id}: {motivo}',
                    usuario=usuario
                )
        
        # Cambiar estado
        venta.estado = 'CANCELADA'
        venta.save()
        
        return venta
    
    @staticmethod
    def obtener_estadisticas_venta(venta_id):
        """
        Obtener estadísticas de una venta específica
        
        Returns:
            dict: Estadísticas de la venta
        """
        venta = Venta.objects.select_related('cliente', 'usuario').prefetch_related(
            'detalles__producto'
        ).get(id=venta_id)
        
        # Calcular estadísticas
        total_productos = venta.detalles.count()
        total_unidades = venta.detalles.aggregate(
            total=Sum('cantidad')
        )['total'] or 0
        
        # Calcular ganancia (si hay datos de precio de compra)
        ganancia_total = Decimal('0.00')
        for detalle in venta.detalles.all():
            costo = detalle.producto.precio_compra * detalle.cantidad
            ingreso = detalle.subtotal
            ganancia_total += (ingreso - costo)
        
        estadisticas = {
            'venta': {
                'id': venta.id,
                'total': float(venta.total),
                'estado': venta.estado,
                'fecha': venta.fecha
            },
            'cliente': {
                'id': venta.cliente.id,
                'nombre': venta.cliente.nombre,
                'documento': venta.cliente.documento
            },
            'usuario': {
                'id': venta.usuario.id,
                'username': venta.usuario.username
            },
            'productos': {
                'total_productos': total_productos,
                'total_unidades': total_unidades
            },
            'financiero': {
                'total_venta': float(venta.total),
                'ganancia_estimada': float(ganancia_total),
                'margen': float((ganancia_total / venta.total * 100)) if venta.total > 0 else 0
            }
        }
        
        return estadisticas
    
    @staticmethod
    def obtener_estadisticas_generales(fecha_inicio=None, fecha_fin=None):
        """
        Obtener estadísticas generales de ventas
        
        Args:
            fecha_inicio: Fecha inicial (opcional)
            fecha_fin: Fecha final (opcional)
        
        Returns:
            dict: Estadísticas generales
        """
        queryset = Venta.objects.all()
        
        # Filtrar por fechas
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Totales por estado
        total_ventas = queryset.count()
        ventas_completadas = queryset.filter(estado='COMPLETADA').count()
        ventas_pendientes = queryset.filter(estado='PENDIENTE').count()
        ventas_canceladas = queryset.filter(estado='CANCELADA').count()
        
        # Totales monetarios
        total_ingresos = queryset.filter(estado='COMPLETADA').aggregate(
            total=Sum('total')
        )['total'] or 0
        
        total_pendiente = queryset.filter(estado='PENDIENTE').aggregate(
            total=Sum('total')
        )['total'] or 0
        
        # Promedio
        promedio_venta = queryset.filter(estado='COMPLETADA').aggregate(
            promedio=Avg('total')
        )['promedio'] or 0
        
        # Top clientes
        top_clientes = queryset.filter(estado='COMPLETADA').values(
            'cliente__nombre',
            'cliente__id'
        ).annotate(
            total_compras=Count('id'),
            total_gastado=Sum('total')
        ).order_by('-total_gastado')[:5]
        
        estadisticas = {
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'totales': {
                'total_ventas': total_ventas,
                'completadas': ventas_completadas,
                'pendientes': ventas_pendientes,
                'canceladas': ventas_canceladas
            },
            'financiero': {
                'total_ingresos': float(total_ingresos),
                'total_pendiente': float(total_pendiente),
                'promedio_venta': float(promedio_venta)
            },
            'top_clientes': list(top_clientes),
            'fecha_consulta': timezone.now()
        }
        
        return estadisticas