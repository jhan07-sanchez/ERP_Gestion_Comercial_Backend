# apps/caja/admin.py
from django.contrib import admin
from .models import MetodoPago, MovimientoCaja

@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'activo')
    list_editable = ('activo',)


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'metodo_pago', 'monto', 'fecha')
    list_filter = ('tipo', 'metodo_pago')
    search_fields = ('descripcion',)
    readonly_fields = ('fecha',)
