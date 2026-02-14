# apps/compras/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Compra, DetalleCompra


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 1
    readonly_fields = ('subtotal',)
    fields = ('producto', 'cantidad', 'precio_compra', 'subtotal',)


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'proveedor', 'total_formateado', 'usuario', 'fecha', 'estado')
    list_filter = ('fecha', 'proveedor', 'estado')
    search_fields = ('proveedor',)
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'
    inlines = [DetalleCompraInline]
    
    fieldsets = (
        ('Información de la Compra', {
            'fields': ('proveedor', 'total', 'estado')
        }),
        ('Usuario y Fecha', {
            'fields': ('usuario', 'fecha')
        }),
    )
    
    def total_formateado(self, obj):
      total = float(obj.total)
      return format_html(
        '<span style="color: blue; font-weight: bold;">${}</span>',
        f'{total:,.2f}'
    )

    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva compra
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


@admin.register(DetalleCompra)
class DetalleCompraAdmin(admin.ModelAdmin):
    list_display = ('id', 'compra', 'producto', 'cantidad', 'precio_compra', 'subtotal_formateado')
    list_filter = ('compra__fecha',)
    search_fields = ('producto__nombre', 'compra__id')
    readonly_fields = ('subtotal',)
    
    def subtotal_formateado(self, obj):
       subtotal = float(obj.subtotal)
       return format_html(
        '<span style="color: blue; font-weight: bold;">${}</span>',
        f'{subtotal:,.2f}'
    )
