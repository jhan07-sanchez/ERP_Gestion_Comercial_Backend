# apps/configuracion/models.py
from django.db import models

class ConfiguracionGeneral(models.Model):
    nombre_empresa = models.CharField(max_length=150)
    nit = models.CharField(max_length=50)
    telefono = models.CharField(max_length=30)
    direccion = models.TextField()

    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    moneda = models.CharField(max_length=10, default='COP')

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuración General"

    def __str__(self):
        return self.nombre_empresa
