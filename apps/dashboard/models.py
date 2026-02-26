from django.db import models
from django.conf import settings


class ActividadSistema(models.Model):
    TIPO_CHOICES = [
        ("CLIENTE", "Cliente"),
        ("PRODUCTO", "Producto"),
        ("VENTA", "Venta"),
        ("COMPRA", "Compra"),
        ("CAJA", "Caja"),
    ]

    ACCION_CHOICES = [
        ("CREADO", "Creado"),
        ("ACTUALIZADO", "Actualizado"),
        ("ELIMINADO", "Eliminado"),
    ]

    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    descripcion = models.TextField()
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, default="COMPLETADO")

    class Meta:
        # db_table define el nombre físico de la tabla en SQL.
        # Es mejor usar 'dashboard_actividad' para evitar conflictos.
        db_table = "dashboard_actividad"

        # Estos nombres son los que aparecerán en el Admin de Django
        verbose_name = "Actividad del Sistema"
        verbose_name_plural = "Actividades del Sistema"

        # El guion '-' en '-fecha' ordena de la más reciente a la más antigua
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.usuario} - {self.tipo} ({self.accion}) - {self.fecha.strftime('%d/%m/%Y')}"
