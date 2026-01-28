from django.db import models
from django.conf import settings
from apps.inventario.models import Producto  # Ajusta según tu estructura


class Compra(models.Model):
    proveedor = models.CharField(max_length=200)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name='compras'
    )

    class Meta:
        db_table = 'compras'
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        ordering = ['-fecha']

    def __str__(self):
        return f"Compra #{self.id} - {self.proveedor} - ${self.total}"


class DetalleCompra(models.Model):
    compra = models.ForeignKey(
        Compra, 
        on_delete=models.CASCADE, 
        related_name='detalles'
    )
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.PROTECT, 
        related_name='detalles_compra'
    )
    cantidad = models.IntegerField()
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_compra'
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'

    def save(self, *args, **kwargs):
        # Calcular subtotal automáticamente
        self.subtotal = self.cantidad * self.precio_compra
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.compra.id} - {self.producto.nombre} x {self.cantidad}"