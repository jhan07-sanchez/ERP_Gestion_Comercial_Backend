from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from django.utils import timezone
from apps.productos.models import Producto
from apps.proveedores.models import Proveedor


class Compra(models.Model):
    ESTADO_COMPRA = [
        ("PENDIENTE", "Pendiente"),
        ("PARCIAL", "Parcial"),
        ("COMPLETADA", "Completada"),
        ("ANULADA", "Anulada"),
    ]

    numero_compra = models.CharField(max_length=20, unique=True, editable=False)

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="compras"
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="compras"
    )

    motivo_anulacion = models.TextField(null=True, blank=True)

    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    fecha = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    estado = models.CharField(max_length=10, choices=ESTADO_COMPRA, default="PENDIENTE")

    class Meta:
        db_table = "compras"
        verbose_name = "Compra"
        verbose_name_plural = "Compras"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["numero_compra"]),
            models.Index(fields=["proveedor"]),
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha"]),
        ]

    def __str__(self):
        return f"{self.numero_compra} - {self.proveedor.nombre} - ${self.total}"

    # 🔹 Generar número automático usando configuración global
    def generar_numero_compra(self):
        from apps.configuracion.services.configuracion_service import ConfiguracionService
        return ConfiguracionService.generar_numero_compra()

    # 🔹 Override save
    def save(self, *args, **kwargs):
        if not self.numero_compra:
            self.numero_compra = self.generar_numero_compra()
        super().save(*args, **kwargs)

    # 🔹 Recalcular total desde detalles
    def recalcular_total(self):
        total = (
            self.detalles.aggregate(total=Sum(F("cantidad") * F("precio_compra")))[
                "total"
            ]
            or 0
        )

        self.total = total
        super().save(update_fields=["total"])


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra, on_delete=models.CASCADE, related_name="detalles"
    )

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="detalles_compra"
    )

    cantidad = models.PositiveIntegerField()

    precio_compra = models.DecimalField(max_digits=12, decimal_places=2)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, editable=False)

    class Meta:
        db_table = "detalle_compra"
        verbose_name = "Detalle de Compra"
        verbose_name_plural = "Detalles de Compra"

    def __str__(self):
        return f"{self.compra.numero_compra} - {self.producto.nombre} x {self.cantidad}"

    # 🔹 Guardar detalle y recalcular total automáticamente
    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_compra
        super().save(*args, **kwargs)
        self.compra.recalcular_total()

    # 🔹 Si se elimina detalle, recalcula total
    def delete(self, *args, **kwargs):
        compra = self.compra
        super().delete(*args, **kwargs)
        compra.recalcular_total()


class PagoCompra(models.Model):
    METODO_PAGO_CHOICES = [
        ("EFECTIVO", "Efectivo"),
        ("TARJETA", "Tarjeta"),
        ("TRANSFERENCIA", "Transferencia"),
        ("YAPE", "Yape"),
        ("PLIN", "Plin"),
        ("CREDITO", "Crédito"),
    ]

    compra = models.ForeignKey(
        Compra, on_delete=models.CASCADE, related_name="pagos"
    )
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    metodo_pago = models.CharField(
        max_length=20, choices=METODO_PAGO_CHOICES, default="EFECTIVO"
    )
    referencia = models.CharField(max_length=100, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pagos_compras_registrados",
    )

    class Meta:
        db_table = "pago_compra"
        verbose_name = "Pago de Compra"
        verbose_name_plural = "Pagos de Compras"
        ordering = ["fecha"]

    def __str__(self):
        return f"Pago #{self.id} de Compra #{self.compra.numero_compra} - ${self.monto}"




class CuentaPorPagar(models.Model):
    """
    Registro de deuda con un proveedor generada por una compra a crédito.

    Flujo:
    1. Se registra pago con método tipo=CREDITO
    2. Se crea esta CuentaPorPagar automáticamente
    3. Cuando el proveedor cobra, se registra el pago real (CONTADO)
       y se reduce saldo_pendiente

    Estados:
    - PENDIENTE  → No se ha abonado nada
    - PARCIAL    → Se han hecho abonos pero queda saldo
    - PAGADO     → Saldo en cero, deuda cancelada
    """

    ESTADO_PENDIENTE = "PENDIENTE"
    ESTADO_PARCIAL = "PARCIAL"
    ESTADO_PAGADO = "PAGADO"

    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PARCIAL, "Parcial"),
        (ESTADO_PAGADO, "Pagado"),
    ]

    compra = models.ForeignKey(
        Compra,
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar",
        help_text="Compra que originó esta deuda",
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="cuentas_por_pagar",
        help_text="Proveedor al que se le debe",
    )
    monto_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Monto original de la deuda",
    )
    saldo_pendiente = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Cuánto falta por pagar",
    )
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE,
        db_index=True,
    )
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha límite de pago acordada con el proveedor (opcional)",
    )
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Notas adicionales sobre la deuda",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cuentas_por_pagar"
        verbose_name = "Cuenta por Pagar"
        verbose_name_plural = "Cuentas por Pagar"
        ordering = ["-fecha_creacion"]
        indexes = [
            models.Index(fields=["proveedor", "estado"]),
            models.Index(fields=["estado", "fecha_vencimiento"]),
        ]

    def __str__(self):
        return (
            f"CPP #{self.id} — {self.proveedor.nombre} "
            f"— Saldo: ${self.saldo_pendiente:,.0f} ({self.estado})"
        )

    @property
    def esta_pagada(self) -> bool:
        return self.estado == self.ESTADO_PAGADO

    @property
    def porcentaje_pagado(self) -> float:
        if self.monto_total == 0:
            return 100.0
        pagado = float(self.monto_total - self.saldo_pendiente)
        return round((pagado / float(self.monto_total)) * 100, 2)