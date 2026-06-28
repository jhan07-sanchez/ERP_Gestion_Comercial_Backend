from django.db import transaction
from apps.facturacion.models import Factura
from apps.inventario.models import Inventario, MovimientoInventario

class InventarioFacturaService:
    """
    Servicio puente entre Facturación e Inventario.
    Se encarga de descontar o revertir el stock de los productos.
    """

    @staticmethod
    def descontar_stock(factura: Factura, usuario):
        """
        Descuenta el stock de los productos al emitir la factura.
        Si la configuración lo impide, esto debería lanzar una excepción, pero
        esa lógica puede validarse antes de invocar esto.
        """
        for detalle in factura.detalles.all():
            producto = detalle.producto
            cantidad = detalle.cantidad
            
            with transaction.atomic():
                # Actualizar el registro del inventario atómicamente
                inventario = Inventario.objects.select_for_update().get(producto=producto)
                inventario.stock_actual -= cantidad
                inventario.save(update_fields=["stock_actual"])
                
                # Registrar el movimiento de salida
                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo_movimiento="SALIDA",
                    cantidad=cantidad,
                    referencia=f"Factura {factura.numero or factura.id}",
                    usuario=usuario
                )

    @staticmethod
    def revertir_stock(factura: Factura, usuario):
        """
        Revierte el stock de los productos al anular la factura.
        """
        for detalle in factura.detalles.all():
            producto = detalle.producto
            cantidad = detalle.cantidad
            
            with transaction.atomic():
                # Actualizar el registro del inventario atómicamente
                inventario = Inventario.objects.select_for_update().get(producto=producto)
                inventario.stock_actual += cantidad
                inventario.save(update_fields=["stock_actual"])
                
                # Registrar el movimiento de entrada
                MovimientoInventario.objects.create(
                    producto=producto,
                    tipo_movimiento="ENTRADA",
                    cantidad=cantidad,
                    referencia=f"Anulación Factura {factura.numero or factura.id}",
                    usuario=usuario
                )
