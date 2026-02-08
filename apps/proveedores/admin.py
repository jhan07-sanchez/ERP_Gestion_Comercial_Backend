# apps/proveedores/admin.py
from django.contrib import admin
from .models import Proveedor

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'documento', 'telefono', 'email', 'estado', 'fecha_creacion')
    list_filter = ('estado',)
    search_fields = ('nombre', 'documento')
    list_editable = ('estado',)
    ordering = ('nombre',)
    readonly_fields = ('fecha_creacion',)