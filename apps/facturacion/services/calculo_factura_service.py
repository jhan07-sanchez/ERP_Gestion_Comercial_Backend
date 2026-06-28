from decimal import Decimal, ROUND_HALF_UP

from apps.configuracion.services.configuracion_service import ConfiguracionService
from apps.facturacion.models import Factura, FacturaImpuesto, Impuesto


class CalculoFacturaService:
    """
    Motor de cálculo para facturación.
    Recalcula subtotales, impuestos por línea y totales de cabecera.
    """

    @staticmethod
    def _porcentaje_iva() -> Decimal:
        config = ConfiguracionService.obtener_configuracion()
        if not config.aplicar_impuesto_por_defecto:
            return Decimal("0.00")
        return Decimal(str(config.impuesto_porcentaje))

    @staticmethod
    def _calcular_impuesto_linea(base_linea: Decimal, porcentaje: Decimal) -> Decimal:
        if porcentaje <= 0 or base_linea <= 0:
            return Decimal("0.00")
        return (base_linea * porcentaje / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    @staticmethod
    def recalcular_totales(factura: Factura) -> Factura:
        """
        Recalcula los montos totales de una factura sumando sus detalles.
        El IVA se aplica sobre (cantidad × precio − descuento) por línea,
        usando el porcentaje configurado globalmente (misma regla que el frontend).
        """
        porcentaje_iva = CalculoFacturaService._porcentaje_iva()
        detalles = factura.detalles.all()

        subtotal_total = Decimal("0.00")
        descuento_total = Decimal("0.00")
        impuestos_total = Decimal("0.00")

        for detalle in detalles:
            cantidad = Decimal(str(detalle.cantidad))
            precio = Decimal(str(detalle.precio_unitario))
            descuento = Decimal(str(detalle.descuento or 0))

            subtotal_linea = (cantidad * precio).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            base_linea = max(Decimal("0.00"), subtotal_linea - descuento)

            # Si el frontend envió impuesto explícito, respetarlo; si no, calcular con IVA global
            impuesto_enviado = detalle.impuestos_linea
            if impuesto_enviado and impuesto_enviado > 0:
                impuestos_linea = Decimal(str(impuesto_enviado)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                impuestos_linea = CalculoFacturaService._calcular_impuesto_linea(
                    base_linea, porcentaje_iva
                )

            detalle.subtotal = subtotal_linea
            detalle.impuestos_linea = impuestos_linea
            detalle.total_linea = base_linea + impuestos_linea
            detalle.save(
                update_fields=["subtotal", "impuestos_linea", "total_linea"]
            )

            subtotal_total += subtotal_linea
            descuento_total += descuento
            impuestos_total += impuestos_linea

        base_imponible = max(Decimal("0.00"), subtotal_total - descuento_total)
        total_calculado = base_imponible + impuestos_total

        factura.subtotal = subtotal_total
        factura.descuento_total = descuento_total
        factura.impuestos_total = impuestos_total
        factura.total = total_calculado

        pagos_realizados = sum(
            Decimal(str(pago.monto)) for pago in factura.pagos.all()
        )
        factura.saldo_pendiente = total_calculado - pagos_realizados

        factura.save(
            update_fields=[
                "subtotal",
                "descuento_total",
                "impuestos_total",
                "total",
                "saldo_pendiente",
            ]
        )

        CalculoFacturaService._actualizar_desglose_impuestos(
            factura, base_imponible, impuestos_total, porcentaje_iva
        )

        return factura

    @staticmethod
    def _actualizar_desglose_impuestos(
        factura: Factura,
        base_imponible: Decimal,
        impuestos_total: Decimal,
        porcentaje_iva: Decimal,
    ) -> None:
        """Mantiene el desglose de impuestos alineado con los totales recalculados."""
        factura.desglose_impuestos.all().delete()

        if impuestos_total <= 0 or porcentaje_iva <= 0:
            return

        impuesto_iva, _ = Impuesto.objects.get_or_create(
            nombre="IVA",
            defaults={"porcentaje": porcentaje_iva, "activo": True},
        )
        if impuesto_iva.porcentaje != porcentaje_iva:
            impuesto_iva.porcentaje = porcentaje_iva
            impuesto_iva.save(update_fields=["porcentaje"])

        FacturaImpuesto.objects.create(
            factura=factura,
            impuesto=impuesto_iva,
            base_imponible=base_imponible,
            monto=impuestos_total,
        )
