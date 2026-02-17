from django.db import models
from django.conf import settings
from django.db.models import Sum, F
from django.utils import timezone
from apps.inventario.models import Producto
from apps.proveedores.models import Proveedor


class Compra(models.Model):
    ESTADO_COMPRA = [
        ("PENDIENTE", "Pendiente"),
        ("ANULADA", "Anulada"),
        ("REALIZADA", "Realizada"),
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

    fecha = models.DateField(default=timezone.now)
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

    # 🔹 Generar número automático tipo COMP-00001
    def generar_numero_compra(self):
        last = Compra.objects.order_by("-id").first()
        if not last:
            return "COMP-00001"

        last_number = int(last.numero_compra.split("-")[-1])
        new_number = last_number + 1
        return f"COMP-{new_number:05d}"

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
