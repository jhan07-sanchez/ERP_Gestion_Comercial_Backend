from django.db import models
from django.conf import settings
from decimal import Decimal
from apps.documentos.models import Documento
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.configuracion.models import MetodoPago, Impuesto, CondicionPago


class Factura(models.Model):
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EMITIDA", "Emitida"),
        ("PARCIAL", "Pagada Parcialmente"),
        ("PAGADA", "Pagada"),
        ("VENCIDA", "Vencida"),
        ("ANULADA", "Anulada"),
    ]

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="facturas")
    # El numero se asigna solo al emitir. En borrador es nulo.
    numero = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="BORRADOR", db_index=True)
    
    # Snapshot fiscal inmutable generado al emitir
    documento = models.OneToOneField(
        Documento, on_delete=models.PROTECT, null=True, blank=True, related_name="factura_origen"
    )

    fecha_emision = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    
    # Condiciones de Pago (Desde Configuración Global)
    condicion_pago = models.ForeignKey(CondicionPago, on_delete=models.PROTECT, null=True, blank=True)

    
    # Totales
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    descuento_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    impuestos_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    saldo_pendiente = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))

    observaciones = models.TextField(blank=True, null=True)
    
    # Auditoría
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="facturas_vendidas", null=True, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="facturas_creadas")
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "facturacion_factura"
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        ordering = ["-fecha_creacion"]
        permissions = [
            ("emitir_factura", "Puede emitir facturas"),
            ("anular_factura", "Puede anular facturas"),
            ("registrar_pago_factura", "Puede registrar pagos en facturas"),
        ]

    def __str__(self):
        return f"Factura {self.numero or 'BORRADOR'} - {self.cliente.nombre}"


class FacturaDetalle(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="detalles_factura")
    
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=2)
    descuento = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    
    # Calculados por línea
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, help_text="Cantidad * Precio")
    impuestos_linea = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_linea = models.DecimalField(max_digits=14, decimal_places=2, help_text="Subtotal - Descuento + Impuestos")

    class Meta:
        db_table = "facturacion_factura_detalle"
        verbose_name = "Detalle de Factura"
        verbose_name_plural = "Detalles de Factura"

    def __str__(self):
        return f"{self.factura} - {self.producto.nombre}"


class FacturaImpuesto(models.Model):
    """
    Desglose de los impuestos aplicados a la factura entera.
    """
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="desglose_impuestos")
    impuesto = models.ForeignKey(Impuesto, on_delete=models.PROTECT)
    base_imponible = models.DecimalField(max_digits=14, decimal_places=2)
    monto = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "facturacion_factura_impuesto"
        unique_together = ("factura", "impuesto")


class PagoFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos")
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    referencia = models.CharField(max_length=100, blank=True, null=True, help_text="Referencia de transferencia/tarjeta")
    observaciones = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pagos_factura_registrados")

    class Meta:
        db_table = "facturacion_pago_factura"
        verbose_name = "Pago de Factura"
        ordering = ["-fecha"]

    def __str__(self):
        return f"Pago {self.id} - Factura {self.factura.id} - ${self.monto}"


class HistorialFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="historial")
    accion = models.CharField(max_length=100)
    descripcion = models.TextField()
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="historial_facturacion")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "facturacion_historial"
        verbose_name = "Historial de Factura"
        verbose_name_plural = "Historiales de Facturas"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.factura.numero or self.factura.id} - {self.accion}"


# ----------------------------------------------------------------------------
# MODELOS EXISTENTES MANTENIDOS (Notas de Crédito y Débito)
# ----------------------------------------------------------------------------

class NotaCredito(models.Model):
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EMITIDA", "Emitida"),
        ("ANULADA", "Anulada"),
    ]
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="notas_credito")
    numero = models.CharField(max_length=50, unique=True, null=True, blank=True)
    motivo = models.TextField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="BORRADOR")
    fecha_emision = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notas_credito_creadas")

    class Meta:
        db_table = "facturacion_nota_credito"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return self.numero or "Nota Crédito Borrador"


class NotaCreditoDetalle(models.Model):
    nota_credito = models.ForeignKey(NotaCredito, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    producto_nombre = models.CharField(max_length=255)
    producto_codigo = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "facturacion_nota_credito_detalle"

    def __str__(self):
        return self.producto_nombre


class NotaDebito(models.Model):
    ESTADO_CHOICES = [
        ("BORRADOR", "Borrador"),
        ("EMITIDA", "Emitida"),
        ("ANULADA", "Anulada"),
    ]
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="notas_debito")
    numero = models.CharField(max_length=50, unique=True, null=True, blank=True)
    motivo = models.TextField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="BORRADOR")
    fecha_emision = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="notas_debito_creadas")

    class Meta:
        db_table = "facturacion_nota_debito"
        ordering = ["-fecha_emision"]

    def __str__(self):
        return self.numero or "Nota Débito Borrador"


class NotaDebitoDetalle(models.Model):
    nota_debito = models.ForeignKey(NotaDebito, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    producto_nombre = models.CharField(max_length=255)
    producto_codigo = models.CharField(max_length=100)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "facturacion_nota_debito_detalle"

    def __str__(self):
        return self.producto_nombre


