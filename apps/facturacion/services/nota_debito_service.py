from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.facturacion.models import (
    Factura, NotaDebito, NotaDebitoDetalle, HistorialFactura
)
from apps.facturacion.services.numeracion_service import NumeracionFacturaService
from apps.documentos.models import Documento, DocumentoDetalle


class NotaDebitoService:
    """
    Servicio de dominio para Notas de Débito.

    Las Notas de Débito incrementan la deuda del cliente sobre una factura existente
    (por conceptos como: intereses por mora, ajustes de precio, cargos adicionales).

    Responsabilidades:
        - Crear borrador de ND asociada a una factura emitida/pagada/parcial.
        - Emitir la ND: genera documento inmutable e incrementa saldo pendiente.
        - Anular una ND emitida y revertir los efectos financieros.

    Reglas de negocio:
        - Solo se puede crear una ND sobre facturas EMITIDA, PARCIAL o PAGADA.
        - Al emitir, el saldo_pendiente de la factura se incrementa.
        - Si la factura estaba PAGADA, pasa a EMITIDA (tiene nueva deuda).
    """

    @staticmethod
    @transaction.atomic
    def crear_borrador(
        factura: Factura,
        motivo: str,
        detalles_data: list,
        usuario
    ) -> NotaDebito:
        """
        Crea una Nota de Débito en estado BORRADOR.

        Args:
            factura: Factura origen.
            motivo: Razón del cargo adicional.
            detalles_data: Lista de dicts con producto_id, cantidad, precio_unitario, etc.
            usuario: Usuario que crea la ND.

        Returns:
            NotaDebito creada.
        """
        estados_validos = ["EMITIDA", "PARCIAL", "PAGADA"]
        if factura.estado not in estados_validos:
            raise ValueError(
                f"Solo se pueden crear Notas de Débito sobre facturas en estado "
                f"{', '.join(estados_validos)}. Estado actual: {factura.estado}"
            )

        if not detalles_data:
            raise ValueError("La Nota de Débito debe contener al menos una línea de detalle.")

        subtotal_nd = Decimal("0.00")
        for item in detalles_data:
            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))
            if cantidad <= 0:
                raise ValueError("Las cantidades deben ser mayores a cero.")
            if precio < 0:
                raise ValueError("Los precios no pueden ser negativos.")
            subtotal_nd += cantidad * precio

        nota_debito = NotaDebito.objects.create(
            factura=factura,
            motivo=motivo,
            subtotal=subtotal_nd,
            impuesto=Decimal("0.00"),
            total=subtotal_nd,
            estado="BORRADOR",
            creado_por=usuario
        )

        for item in detalles_data:
            producto = None
            producto_nombre = item.get('producto_nombre', 'Concepto')
            producto_codigo = item.get('producto_codigo', 'N/A')

            if 'producto_id' in item and item['producto_id']:
                from apps.productos.models import Producto
                producto = Producto.objects.get(pk=item['producto_id'])
                producto_nombre = producto.nombre
                producto_codigo = producto.codigo

            cantidad = Decimal(str(item['cantidad']))
            precio = Decimal(str(item['precio_unitario']))

            NotaDebitoDetalle.objects.create(
                nota_debito=nota_debito,
                producto=producto,
                producto_nombre=producto_nombre,
                producto_codigo=producto_codigo,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=cantidad * precio
            )

        HistorialFactura.objects.create(
            factura=factura,
            accion="ND BORRADOR CREADA",
            descripcion=f"Nota de Débito #{nota_debito.id} creada. Motivo: {motivo}. Monto: ${subtotal_nd}",
            usuario=usuario
        )

        return nota_debito

    @staticmethod
    @transaction.atomic
    def emitir(nota_debito: NotaDebito, usuario) -> NotaDebito:
        """
        Emite una Nota de Débito: asigna consecutivo, genera documento inmutable
        e incrementa el saldo pendiente de la factura.
        """
        if nota_debito.estado != "BORRADOR":
            raise ValueError("Solo se pueden emitir Notas de Débito en estado BORRADOR.")

        factura = nota_debito.factura

        if factura.estado in ["ANULADA", "BORRADOR"]:
            raise ValueError(
                f"No se puede emitir una ND sobre una factura en estado {factura.estado}."
            )

        # 1. Consecutivo
        nota_debito.numero = NumeracionFacturaService.generar_siguiente_numero(
            codigo_secuencia="nota_debito"
        )
        nota_debito.estado = "EMITIDA"
        nota_debito.save(update_fields=["numero", "estado"])

        # 2. Documento inmutable
        documento = Documento.objects.create(
            tipo=Documento.TipoDocumento.FACTURA_VENTA,
            estado=Documento.Estado.EMITIDO,
            numero_interno=nota_debito.numero,
            referencia_operacion=f"ND sobre Factura {factura.numero or factura.id}",
            subtotal=nota_debito.subtotal,
            impuestos=nota_debito.impuesto,
            total=nota_debito.total,
            usuario=usuario,
            notas=f"Nota de Débito. Motivo: {nota_debito.motivo}"
        )

        orden = 1
        for detalle in nota_debito.detalles.all():
            DocumentoDetalle.objects.create(
                documento=documento,
                orden=orden,
                descripcion=f"ND: {detalle.producto_nombre}",
                producto_id=detalle.producto.id if detalle.producto else None,
                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                subtotal=detalle.subtotal
            )
            orden += 1

        documento.generar_hash()

        # 3. Incrementar saldo pendiente de la factura
        factura.saldo_pendiente += nota_debito.total

        # Si la factura estaba PAGADA, ahora tiene deuda nueva → EMITIDA
        if factura.estado == "PAGADA":
            factura.estado = "EMITIDA"

        factura.save(update_fields=["saldo_pendiente", "estado"])

        # 4. Trazabilidad
        HistorialFactura.objects.create(
            factura=factura,
            accion="ND EMITIDA",
            descripcion=(
                f"Nota de Débito {nota_debito.numero} emitida por ${nota_debito.total}. "
                f"Nuevo saldo pendiente: ${factura.saldo_pendiente}"
            ),
            usuario=usuario
        )

        return nota_debito

    @staticmethod
    @transaction.atomic
    def anular(nota_debito: NotaDebito, usuario, motivo: str) -> NotaDebito:
        """
        Anula una Nota de Débito emitida, revirtiendo el incremento en el saldo.
        """
        if nota_debito.estado != "EMITIDA":
            raise ValueError("Solo se pueden anular Notas de Débito en estado EMITIDA.")

        nota_debito.estado = "ANULADA"
        nota_debito.save(update_fields=["estado"])

        factura = nota_debito.factura

        # Revertir incremento de saldo
        factura.saldo_pendiente = max(
            Decimal("0.00"),
            factura.saldo_pendiente - nota_debito.total
        )
        if factura.saldo_pendiente <= Decimal("0.00") and factura.estado in ["EMITIDA", "PARCIAL"]:
            factura.estado = "PAGADA"
        factura.save(update_fields=["saldo_pendiente", "estado"])

        HistorialFactura.objects.create(
            factura=factura,
            accion="ND ANULADA",
            descripcion=f"Nota de Débito {nota_debito.numero} anulada. Motivo: {motivo}",
            usuario=usuario
        )

        return nota_debito
