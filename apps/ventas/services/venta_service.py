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

from apps.configuracion.services.configuracion_service import ConfiguracionService

from apps.ventas.models import Venta, DetalleVenta, PagoVenta
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.inventario.models import Inventario, MovimientoInventario
from apps.caja.services.caja_service import CajaService
from apps.caja.models import MetodoPago

class VentaService:
    """Servicio para manejar la lógica de negocio de Ventas"""
    
    @staticmethod
    @transaction.atomic
    def crear_venta(cliente_id, detalles, usuario, estado='PENDIENTE', tipo_documento='FACTURA'):
        """
        Crear una nueva venta con sus detalles gobernada por la configuración global.
        """
        # 0. Obtener configuración central
        config = ConfiguracionService.obtener_configuracion()
        
        # 1. Obtener el cliente
        cliente = Cliente.objects.get(id=cliente_id)
        
        # 2. Calcular totales con base en impuestos globales
        total_base = Decimal('0.00')
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            cantidad = Decimal(str(detalle['cantidad']))
            
            # Validación de Stock (Regla de Negocio Centralizada)
            if not config.permitir_venta_sin_stock:
                inventario = Inventario.objects.get(producto=producto)
                if inventario.stock_actual < cantidad:
                    raise ValueError(f"Stock insuficiente para {producto.nombre}. Disponible: {inventario.stock_actual}")
            
            precio = Decimal(str(detalle.get('precio_unitario', producto.precio_venta)))
            total_base += precio * cantidad
        
        # Aplicar impuesto global
        porcentaje_iva = config.impuesto_porcentaje if config.aplicar_impuesto_por_defecto else Decimal('0.00')
        impuesto = total_base * (porcentaje_iva / 100)
        total_venta = total_base + impuesto
        
        # 3. Crear la venta
        venta = Venta.objects.create(
            cliente=cliente,
            usuario=usuario,
            total=total_venta,
            impuesto=impuesto,
            estado=estado,
            tipo_documento=tipo_documento
        )
        
        # 4. Crear detalles
        for detalle in detalles:
            producto = Producto.objects.get(id=detalle['producto_id'])
            precio = Decimal(str(detalle.get('precio_unitario', producto.precio_venta)))
            cantidad = Decimal(str(detalle['cantidad']))
            subtotal = precio * cantidad
            
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
    def actualizar_venta(venta_id, cliente_id, detalles, usuario):
        """
        Actualizar una venta existente y sus detalles
        
        Args:
            venta_id: ID de la venta a actualizar
            cliente_id: Nuevo ID del cliente
            detalles: Nueva lista de detalles (producto_id, cantidad, precio_unitario)
            usuario: Usuario que realiza la actualización
            
        Proceso:
            1. Validar que la venta esté PENDIENTE
            2. Actualizar cliente
            3. Eliminar detalles anteriores
            4. Crear nuevos detalles
            5. Recalcular total
        """
        venta = Venta.objects.get(id=venta_id)
        
        # 1. Validar estado (Solo se editan ventas PENDIENTES)
        if venta.estado != 'PENDIENTE':
            raise ValueError(
                f'Solo se pueden editar ventas en estado PENDIENTE. '
                f'Estado actual: {venta.estado}'
            )
            
        # 2. Actualizar cliente
        cliente = Cliente.objects.get(id=cliente_id)
        venta.cliente = cliente
        
        # 3. Eliminar detalles anteriores y volver a crear
        venta.detalles.all().delete()
        
        # 4. Crear nuevos detalles y calcular total
        total = Decimal('0.00')
        for det in detalles:
            producto = Producto.objects.get(id=det['producto_id'])
            precio = det.get('precio_unitario', producto.precio_venta)
            cantidad = det['cantidad']
            subtotal = Decimal(str(precio)) * Decimal(str(cantidad))
            total += subtotal
            
            DetalleVenta.objects.create(
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=subtotal
            )
            
        # 5. Actualizar total y guardar
        venta.total = total
        venta.save()
        
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
            
        # Mapear el string metodo_pago al modelo MetodoPago de Caja
        metodo_caja = MetodoPago.objects.filter(nombre__iexact=metodo_pago, activo=True).first()
        
        # Si no lo encuentra por nombre exacto, intentar por el primero activo
        if not metodo_caja:
            metodo_caja = MetodoPago.objects.filter(activo=True).first()
            
        if not metodo_caja:
            raise ValueError(
                "No hay métodos de pago activos configurados en el módulo de Caja. "
                "Por favor, contacte al administrador para inicializar los métodos de pago."
            )
        
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

        # REGLA ERP: Llamar a la caja y registrar el ingreso
        # Esto fallará si el usuario no tiene caja abierta (CajaCerradaOperacionError)
        CajaService.registrar_pago_venta(
            venta=venta,
            usuario=usuario,
            metodo_pago_id=metodo_caja.id,
            monto=monto_decimal
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

        # Documento ERP (factura / ticket): misma transacción; fallo → rollback total
        if venta.estado == 'COMPLETADA':
            from apps.documentos.services import DocumentoService
            from apps.documentos.exceptions import DocumentoError

            try:
                DocumentoService.crear_documento_venta(venta, usuario)
            except DocumentoError as exc:
                raise ValueError(
                    f"No se pudo generar el documento de la venta: {exc}"
                ) from exc
        
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

        from apps.documentos.services import DocumentoService
        from apps.documentos.exceptions import DocumentoError

        try:
            DocumentoService.crear_documento_venta(venta, usuario)
        except DocumentoError as exc:
            raise ValueError(
                f"No se pudo generar el documento de la venta: {exc}"
            ) from exc
        
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