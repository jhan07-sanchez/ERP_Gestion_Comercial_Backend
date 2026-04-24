from django.contrib import admin
from .models import ListaPrecioCompra

@admin.register(ListaPrecioCompra)
class ListaPrecioCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'proveedor', 'precio', 'vigente', 'fecha_inicio')
    list_filter = ('vigente', 'proveedor')
    search_fields = ('producto__nombre', 'proveedor__nombre')
    ordering = ('fecha_inicio',)

