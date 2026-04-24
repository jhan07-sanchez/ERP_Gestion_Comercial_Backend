from django.db import models
from django.utils import timezone
from django.db.models import Q, UniqueConstraint


class ListaPrecioCompra(models.Model):
    producto = models.ForeignKey(
        'productos.producto',
        on_delete=models.CASCADE,
        related_name='precios_compra'
    )
    proveedor = models.ForeignKey(
        'proveedores.proveedor',
        on_delete=models.CASCADE,
        related_name='precios_productos'
    )

    precio = models.DecimalField(max_digits=10, decimal_places=2)

    vigente = models.BooleanField(default=True)

    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lista_precio_compra'
        verbose_name = 'Lista de precio de compra'
        verbose_name_plural = 'Lista de precios de compra'
        constraints = [
            UniqueConstraint(
                fields=['producto', 'proveedor'],
                condition=Q(vigente=True),
                name= 'unique_precio_vigente_por_producto_proveedor'
            )

        ]

    def __str__(self):
        return f"{self.producto} - {self.proveedor} - {self.precio}"
