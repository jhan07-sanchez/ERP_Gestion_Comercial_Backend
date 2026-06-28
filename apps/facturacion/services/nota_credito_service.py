from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.facturacion.models import (
    Factura, NotaCredito, NotaCreditoDetalle, HistorialFactura
)
from apps.facturacion.services.numeracion_service import NumeracionFacturaService
from apps.facturacion.services.inventario_factura_service import InventarioFacturaService
from apps.documentos.models import Documento, DocumentoDetalle
from apps.caja.services.caja_service import CajaService
from apps.caja.services.caja_control import CajaControlService
from apps.caja.models import MovimientoCaja


class NotaCreditoService:
    """
    Servicio de dominio para Notas de Crédito.

    Responsabilidades:
        - Crear borrador de NC asociada a una factura emitida/pagada.
        - Emitir la NC: genera documento inmutable y, según política,
          registra saldo a favor (Escenario A) o reembolso en caja (Escenario B).
        - Revertir inventario si aplica devolución física de productos.
        - Anular una NC emitida.

    Reglas de negocio:
        - Solo se puede crear una NC sobre facturas EMITIDA, PARCIAL o PAGADA.
        - El monto total de la NC no puede superar el total de la factura original.
        - El monto acumulado de todas las NC activas no puede superar el total facturado.
        - Si la factura NO está pagada, no se permite reembolso (solo saldo a favor).
    """

    @staticmethod
    @transaction.atomic
    def crear_borrador(
        factura: Factura,
        motivo: str,
        detalles_data: list,
        usuario
    ) -> NotaCredito:
        """
        Crea una Nota de Crédito en estado BORRADOR asociada a una factura.

        Args:
            factura: Factura origen (debe estar EMITIDA, PARCIAL o PAGADA).
            motivo: Razón de la nota de crédito.
            detalles_data: Lista de dicts con producto_id, cantidad, precio_unitario.
            usuario: Usuario que realiza la operación.

        Returns:
            NotaCredito creada.

        Raises:
            ValueError: Si la factura no está en un estado válido o los montos exceden.
        """
        estados_validos = ["EMITIDA", "PARCIAL", "PAGADA"]
        if factura.estado not in estados_validos:
            raise ValueError(
                f"Solo se pueden crear Notas de Crédito sobre facturas en estado "
                f"{', '.join(estados_validos)}. Estado actual: {factura.estado}"
            )

        if not detalles_data:
            raise ValueError("La Nota de Crédito debe contener al menos una línea de detalle.")

        # Calcular totales de la NC
        subtotal_nc = Decimal("0.00")
        for item in detalles_data:
            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))
            if cantidad <= 0:
                raise ValueError("Las cantidades deben ser mayores a cero.")
            if precio < 0:
                raise ValueError("Los precios no pueden ser negativos.")
            subtotal_nc += cantidad * precio

        # Validar que no exceda el total de la factura
        # Considerar NC anteriores activas (no anuladas)
        nc_previas_total = sum(
            nc.total for nc in factura.notas_credito.exclude(estado="ANULADA")
        )
        if (nc_previas_total + subtotal_nc) > factura.total:
            raise ValueError(
                f"El monto acumulado de Notas de Crédito (${nc_previas_total + subtotal_nc}) "
                f"excede el total de la factura (${factura.total})."
            )

        # Crear la NC
        nota_credito = NotaCredito.objects.create(
            factura=factura,
            motivo=motivo,
            subtotal=subtotal_nc,
            impuesto=Decimal("0.00"),
            total=subtotal_nc,
            estado="BORRADOR",
            creado_por=usuario
        )

        # Crear detalles
        for item in detalles_data:
            producto = None
            producto_nombre = item.get('producto_nombre', 'Producto')
            producto_codigo = item.get('producto_codigo', 'N/A')

            if 'producto_id' in item and item['producto_id']:
                from apps.productos.models import Producto
                producto = Producto.objects.get(pk=item['producto_id'])
                producto_nombre = producto.nombre
                producto_codigo = producto.codigo

            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))

            NotaCreditoDetalle.objects.create(
                nota_credito=nota_credito,
                producto=producto,
                producto_nombre=producto_nombre,
                producto_codigo=producto_codigo,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=cantidad * precio
            )

        HistorialFactura.objects.create(
            factura=factura,
            accion="NC BORRADOR CREADA",
            descripcion=f"Nota de Crédito #{nota_credito.id} creada. Motivo: {motivo}. Monto: ${subtotal_nc}",
            usuario=usuario
        )

        return nota_credito

    @staticmethod
    @transaction.atomic
    def emitir(
        nota_credito: NotaCredito,
        usuario,
        tipo_aplicacion: str = "SALDO_FAVOR",
        revertir_inventario: bool = False
    ) -> NotaCredito:
        """
        Emite una Nota de Crédito y ejecuta la política financiera elegida.

        Args:
            nota_credito: NC en estado BORRADOR.
            usuario: Usuario que emite.
            tipo_aplicacion: "SALDO_FAVOR" (Escenario A) o "REEMBOLSO" (Escenario B).
            revertir_inventario: Si True, reingresa los productos al inventario.

        Returns:
            NotaCredito emitida.

        Raises:
            ValueError: Si la NC no está en BORRADOR o el reembolso no aplica.
        """
        if nota_credito.estado != "BORRADOR":
            raise ValueError("Solo se pueden emitir Notas de Crédito en estado BORRADOR.")

        factura = nota_credito.factura

        # Validar que la factura siga en estado válido
        if factura.estado in ["ANULADA", "BORRADOR"]:
            raise ValueError(
                f"No se puede emitir una NC sobre una factura en estado {factura.estado}."
            )

        # Validación: reembolso solo si la factura ya fue pagada
        if tipo_aplicacion == "REEMBOLSO" and factura.estado not in ["PAGADA", "PARCIAL"]:
            raise ValueError(
                "El reembolso directo solo aplica para facturas con pagos registrados."
            )

        # 1. Asignar consecutivo
        nota_credito.numero = NumeracionFacturaService.generar_siguiente_numero(
            codigo_secuencia="nota_credito"
        )
        nota_credito.estado = "EMITIDA"
        nota_credito.save(update_fields=["numero", "estado"])

        # 2. Generar Documento inmutable
        documento = Documento.objects.create(
            tipo=Documento.TipoDocumento.FACTURA_VENTA,
            estado=Documento.Estado.EMITIDO,
            numero_interno=nota_credito.numero,
            referencia_operacion=f"NC sobre Factura {factura.numero or factura.id}",
            subtotal=nota_credito.subtotal,
            impuestos=nota_credito.impuesto,
            total=nota_credito.total,
            usuario=usuario,
            notas=f"Nota de Crédito. Motivo: {nota_credito.motivo}"
        )

        orden = 1
        for detalle in nota_credito.detalles.all():
            DocumentoDetalle.objects.create(
                documento=documento,
                orden=orden,
                descripcion=f"NC: {detalle.producto_nombre}",
                producto_id=detalle.producto.id if detalle.producto else None,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal
            )
            orden += 1

        documento.generar_hash()

        # 3. Aplicar política financiera
        descripcion_historial = f"Nota de Crédito {nota_credito.numero} emitida por ${nota_credito.total}."

        if tipo_aplicacion == "REEMBOLSO":
            # Escenario B: Egreso en Caja
            sesion = CajaControlService.verificar_caja_abierta(usuario)
            CajaService.registrar_movimiento(
                sesion_id=sesion.id,
                tipo=MovimientoCaja.EGRESO_RETIRO,
                monto=nota_credito.total,
                descripcion=(
                    f"Reembolso por Nota de Crédito {nota_credito.numero} "
                    f"(Factura {factura.numero or factura.id})"
                ),
                metodo_pago_id=None,
                usuario=usuario
            )
            descripcion_historial += " Tipo: Reembolso directo en Caja."
        else:
            # Escenario A: Saldo a favor — ajustar saldo pendiente de la factura
            factura.saldo_pendiente = max(
                Decimal("0.00"),
                factura.saldo_pendiente - nota_credito.total
            )
            # Si el saldo llega a 0 y la factura estaba emitida, marcar como pagada
            if factura.saldo_pendiente <= Decimal("0.00") and factura.estado == "EMITIDA":
                factura.estado = "PAGADA"
            factura.save(update_fields=["saldo_pendiente", "estado"])
            descripcion_historial += " Tipo: Saldo a favor del cliente."

        # 4. Revertir inventario si aplica devolución física
        if revertir_inventario:
            NotaCreditoService._revertir_inventario_nc(nota_credito, usuario)
            descripcion_historial += " Se reingresó inventario."

        # 5. Trazabilidad
        HistorialFactura.objects.create(
            factura=factura,
            accion="NC EMITIDA",
            descripcion=descripcion_historial,
            usuario=usuario
        )

        return nota_credito

    @staticmethod
    @transaction.atomic
    def anular(nota_credito: NotaCredito, usuario, motivo: str) -> NotaCredito:
        """
        Anula una Nota de Crédito emitida.
        Revierte los efectos financieros e inventario si los hubo.
        """
        if nota_credito.estado != "EMITIDA":
            raise ValueError("Solo se pueden anular Notas de Crédito en estado EMITIDA.")

        nota_credito.estado = "ANULADA"
        nota_credito.save(update_fields=["estado"])

        factura = nota_credito.factura

        # Revertir ajuste de saldo a favor (incrementar deuda original)
        factura.saldo_pendiente = min(
            factura.total,
            factura.saldo_pendiente + nota_credito.total
        )
        # Si la factura estaba PAGADA y ahora tiene saldo, volver a EMITIDA
        if factura.saldo_pendiente > Decimal("0.00") and factura.estado == "PAGADA":
            factura.estado = "EMITIDA"
        factura.save(update_fields=["saldo_pendiente", "estado"])

        HistorialFactura.objects.create(
            factura=factura,
            accion="NC ANULADA",
            descripcion=f"Nota de Crédito {nota_credito.numero} anulada. Motivo: {motivo}",
            usuario=usuario
        )

        return nota_credito

    @staticmethod
    def _revertir_inventario_nc(nota_credito: NotaCredito, usuario):
        """
        Reingresa al inventario los productos de la Nota de Crédito.
        """
        from apps.inventario.models import Inventario, MovimientoInventario

        for detalle in nota_credito.detalles.select_related('producto').all():
            if detalle.producto is None:
                continue

            inventario = Inventario.objects.select_for_update().get(producto=detalle.producto)
            inventario.stock_actual += detalle.cantidad
            inventario.save(update_fields=["stock_actual"])

            MovimientoInventario.objects.create(
                producto=detalle.producto,
                tipo_movimiento="ENTRADA",
                cantidad=detalle.cantidad,
                referencia=f"Nota de Crédito {nota_credito.numero}",
                usuario=usuario
            )
