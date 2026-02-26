# apps/productos/models.py
from django.db import models
from apps.categorias.models import Categoria


class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_ingreso = models.DateField()
    stock_minimo = models.IntegerField(default=0)
    estado = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'productos'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self.generar_siguiente_codigo()
        super().save(*args, **kwargs)

    @staticmethod
    def generar_siguiente_codigo():
        ultimo = Producto.objects.filter(codigo__startswith="PROD-") \
                                .order_by('-codigo') \
                                .first()

        if ultimo:
            numero = int(ultimo.codigo.split('-')[1])
            siguiente = numero + 1
        else:
            siguiente = 1

        return f"PROD-{siguiente:04d}"
