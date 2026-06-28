from decimal import Decimal
from django.db import transaction
from apps.facturacion.models import Factura, PagoFactura, HistorialFactura
from apps.caja.services.caja_service import CajaService
from apps.caja.services.caja_control import CajaControlService
from apps.caja.models import MovimientoCaja

class PagoFacturaService:
    """
    Servicio para el registro de pagos a facturas.
    Se integra de forma sincrónica con el módulo de Caja para garantizar consistencia financiera.
    """

    @staticmethod
    def registrar_pago(factura: Factura, metodo_pago_id: int, monto: Decimal, usuario, referencia: str = "", observaciones: str = "") -> PagoFactura:
        """
        Registra un pago para una factura y lo refleja inmediatamente en la caja activa del usuario.
        """
        if factura.estado not in ["EMITIDA", "PARCIAL", "VENCIDA"]:
            raise ValueError(f"No se puede registrar pago a una factura en estado {factura.estado}")
            
        if monto <= 0:
            raise ValueError("El monto del pago debe ser mayor a cero")
            
        if monto > factura.saldo_pendiente:
            raise ValueError(f"El monto (${monto}) excede el saldo pendiente de la factura (${factura.saldo_pendiente})")

        with transaction.atomic():
            # 1. Verificar que el usuario tenga una sesión de caja abierta (lanza error si no)
            sesion = CajaControlService.verificar_caja_abierta(usuario)
            
            # 2. Registrar el pago en el módulo de facturación
            pago = PagoFactura.objects.create(
                factura=factura,
                metodo_pago_id=metodo_pago_id,
                monto=monto,
                referencia=referencia,
                observaciones=observaciones,
                registrado_por=usuario
            )
            
            # 3. Actualizar el saldo de la factura y su estado
            factura.saldo_pendiente -= monto
            if factura.saldo_pendiente <= Decimal("0.00"):
                factura.estado = "PAGADA"
            else:
                factura.estado = "PARCIAL"
            
            factura.save(update_fields=["saldo_pendiente", "estado"])
            
            # 4. Registrar el movimiento sincrónico en la Caja (Atómico)
            CajaService.registrar_movimiento(
                sesion_id=sesion.id,
                tipo=MovimientoCaja.INGRESO_VENTA,  # Usamos INGRESO_VENTA para compatibilidad de arqueos
                monto=monto,
                descripcion=f"Pago de Factura {factura.numero or factura.id} - Ref: {referencia}",
                metodo_pago_id=metodo_pago_id,
                usuario=usuario
            )
            # 5. Registro Histórico
            HistorialFactura.objects.create(
                factura=factura,
                accion="PAGO REGISTRADO",
                descripcion=f"Se registró un pago por ${monto} con {pago.metodo_pago.nombre}. Ref: {referencia}",
                usuario=usuario
            )
            
            return pago
