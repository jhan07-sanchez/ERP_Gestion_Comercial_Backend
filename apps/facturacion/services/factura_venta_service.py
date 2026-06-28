from django.db import transaction
from django.utils import timezone
from apps.facturacion.models import Factura, FacturaDetalle, FacturaImpuesto
from apps.facturacion.services.calculo_factura_service import CalculoFacturaService
from apps.facturacion.services.numeracion_service import NumeracionFacturaService
from apps.facturacion.services.inventario_factura_service import InventarioFacturaService
from apps.documentos.models import Documento, DocumentoDetalle
from apps.facturacion.models import HistorialFactura
from apps.caja.services.caja_service import CajaService
from apps.caja.services.caja_control import CajaControlService
from apps.caja.models import MovimientoCaja

class FacturaVentaService:
    """
    Servicio principal para el ciclo de vida de la Factura de Venta.
    """

    @staticmethod
    @transaction.atomic
    def crear_borrador(cliente_id: int, vendedor_id: int, detalles_data: list, usuario, fecha_emision=None, fecha_vencimiento=None, observaciones="") -> Factura:
        """
        Crea una factura en estado BORRADOR con sus detalles.
        """
        factura = Factura.objects.create(
            cliente_id=cliente_id,
            vendedor_id=vendedor_id,
            fecha_emision=fecha_emision,
            fecha_vencimiento=fecha_vencimiento,
            observaciones=observaciones,
            creado_por=usuario,
            estado="BORRADOR"
        )
        
        for item in detalles_data:
            print("ANTES DEL CREATE")
            
            FacturaDetalle.objects.create(
                factura=factura,
                producto_id=item['producto_id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                descuento=item.get('descuento', 0),
                subtotal=0,
                impuestos_linea=item.get('impuestos_linea', 0),
                total_linea=0
                # subtotal y total_linea se calculan en el servicio de calculo
            )

            print("DESPUÉS DEL CREATE")

        print("ANTES DEL RECALCULO")    
        factura = CalculoFacturaService.recalcular_totales(factura)
        
        HistorialFactura.objects.create(
            factura=factura,
            accion="CREACIÓN BORRADOR",
            descripcion="Se creó la factura en estado borrador.",
            usuario=usuario
        )
        return factura

    @staticmethod
    @transaction.atomic
    def actualizar_borrador(factura: Factura, cliente_id: int, detalles_data: list, usuario, vendedor_id: int = None, fecha_emision=None, fecha_vencimiento=None, observaciones: str = "") -> Factura:
        """
        Actualiza un borrador reemplazando todas sus líneas de detalle.
        """
        if factura.estado != "BORRADOR":
            raise ValueError("Solo se pueden editar facturas en estado BORRADOR.")

        # 1. Actualizar cabecera
        factura.cliente_id = cliente_id
        factura.vendedor_id = vendedor_id
        factura.fecha_emision = fecha_emision
        factura.fecha_vencimiento = fecha_vencimiento
        factura.observaciones = observaciones
        factura.save()

        # 2. Reemplazo total de líneas (Hard Delete de detalles previos)
        factura.detalles.all().delete()

        # 3. Crear nuevos detalles
        for item in detalles_data:
            FacturaDetalle.objects.create(
                factura=factura,
                producto_id=item['producto_id'],
                cantidad=item['cantidad'],
                precio_unitario=item['precio_unitario'],
                descuento=item.get('descuento', 0),
                impuestos_linea=item.get('impuestos_linea', 0)
            )

        # 4. Recalcular e historizar
        factura = CalculoFacturaService.recalcular_totales(factura)
        
        HistorialFactura.objects.create(
            factura=factura,
            accion="ACTUALIZACIÓN BORRADOR",
            descripcion="Se actualizaron los datos y/o líneas del borrador.",
            usuario=usuario
        )
        
        return factura

    @staticmethod
    @transaction.atomic
    def emitir_factura(factura: Factura, usuario) -> Factura:
        """
        Transiciona una factura de BORRADOR a EMITIDA.
        - Asigna consecutivo oficial.
        - Genera snapshot en Documento (inmutable).
        - Descuenta stock.
        """
        if factura.estado != "BORRADOR":
            raise ValueError(f"Solo se pueden emitir facturas en estado BORRADOR. Actual: {factura.estado}")
            
        # 1. Asignar Número Oficial
        factura.numero = NumeracionFacturaService.generar_siguiente_numero()
        now = timezone.now()
        
        if factura.fecha_emision and factura.fecha_vencimiento:
            dias_plazo = (factura.fecha_vencimiento - factura.fecha_emision.date()).days
            factura.fecha_emision = now
            if dias_plazo > 0:
                factura.fecha_vencimiento = now.date() + timezone.timedelta(days=dias_plazo)
            else:
                factura.fecha_vencimiento = now.date()
        else:
            factura.fecha_emision = now
        
        # 2. Generar Documento Inmutable
        documento = Documento.objects.create(
            tipo=Documento.TipoDocumento.FACTURA_VENTA,
            estado=Documento.Estado.EMITIDO,
            numero_interno=factura.numero,
            subtotal=factura.subtotal,
            impuestos=factura.impuestos_total,
            total=factura.total,
            fecha_vencimiento=factura.fecha_vencimiento,
            usuario=usuario
        )
        
        # Generar detalles inmutables
        orden = 1
        for detalle in factura.detalles.all():
            DocumentoDetalle.objects.create(
                documento=documento,
                orden=orden,
                descripcion=detalle.producto.nombre,
                producto_id=detalle.producto.id,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.total_linea  # Mapeamos total_linea de factura al subtotal de documento
            )
            orden += 1
            
        # Generar Hash de integridad
        documento.generar_hash()
        
        # 3. Asociar documento a factura y cambiar estado
        factura.documento = documento
        factura.estado = "EMITIDA"
        factura.save()
        
        # 4. Descontar stock
        InventarioFacturaService.descontar_stock(factura, usuario)
        
        # 5. Registro Histórico
        HistorialFactura.objects.create(
            factura=factura,
            accion="EMISIÓN",
            descripcion=f"Factura emitida con número {factura.numero}.",
            usuario=usuario
        )
        
        return factura

    @staticmethod
    @transaction.atomic
    def anular_factura(factura: Factura, usuario, motivo: str) -> Factura:
        """
        Anula una factura EMITIDA o PARCIAL/PAGADA.
        - Reutiliza lógica de Documento.
        - Revierte stock.
        - Si tiene pagos parciales/totales, los revierte sincrónicamente en la Caja.
        """
        if factura.estado not in ["EMITIDA", "VENCIDA", "PARCIAL", "PAGADA"]:
            raise ValueError("Solo se pueden anular facturas que ya han sido emitidas.")
            
        # 1. Reversión sincrónica de pagos en Caja si existen
        if factura.pagos.exists():
            # Requiere caja abierta para sacar el dinero devuelto
            sesion = CajaControlService.verificar_caja_abierta(usuario)
            for pago in factura.pagos.all():
                CajaService.registrar_movimiento(
                    sesion_id=sesion.id,
                    tipo=MovimientoCaja.EGRESO_RETIRO, # Retiro de dinero por devolución
                    monto=pago.monto,
                    descripcion=f"Devolución por anulación de Factura {factura.numero or factura.id} (Pago ID: {pago.id})",
                    metodo_pago_id=pago.metodo_pago_id,
                    usuario=usuario
                )
            
        # 2. Revertir Stock
        InventarioFacturaService.revertir_stock(factura, usuario)
        
        # 3. Anular Documento
        if factura.documento:
            documento = factura.documento
            documento.estado = Documento.Estado.ANULADO
            documento.notas = f"Motivo anulación: {motivo}"
            documento.save(update_fields=["estado", "notas"])
            
        # 4. Anular Factura
        factura.estado = "ANULADA"
        factura.saldo_pendiente = factura.total  # O 0, pero comercialmente la deuda queda inactiva
        factura.observaciones = f"{(factura.observaciones or '')}\nAnulada: {motivo}"
        factura.save(update_fields=["estado", "saldo_pendiente", "observaciones"])
        
        # 5. Registro Histórico
        HistorialFactura.objects.create(
            factura=factura,
            accion="ANULACIÓN",
            descripcion=f"Factura anulada. Motivo: {motivo}. " + ("Se revirtieron pagos en caja." if factura.pagos.exists() else ""),
            usuario=usuario
        )
        
        return factura
