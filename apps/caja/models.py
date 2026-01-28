# apps/caja/models.py
from django.db import models

class MetodoPago(models.Model):
    nombre = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"

    def __str__(self):
        return self.nombre


class MovimientoCaja(models.Model):
    INGRESO = 'INGRESO'
    EGRESO = 'EGRESO'

    TIPO_CHOICES = [
        (INGRESO, 'Ingreso'),
        (EGRESO, 'Egreso'),
    ]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    metodo_pago = models.ForeignKey(MetodoPago, on_delete=models.PROTECT)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.tipo} - {self.monto}"
class CajaDiaria(models.Model):
    fecha = models.DateField(auto_now_add=True)
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Caja Diaria"
        verbose_name_plural = "Cajas Diarias"
        ordering = ['-fecha']

    def __str__(self):
        return f"Caja del {self.fecha}"