# apps/inventario/admin.py
from django.contrib import admin
from django.utils.html import format_html
from apps.inventario.models import Inventario, MovimientoInventario


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'producto', 'stock_actual', 'estado_stock', 'fecha_actualizacion')
    list_filter = ('fecha_actualizacion',)
    search_fields = ('producto__nombre', 'producto__codigo')
    readonly_fields = ('fecha_actualizacion',)

    def estado_stock(self, obj):
        if obj.stock_actual <= obj.producto.stock_minimo:
            return format_html('<span style="color: red; font-weight: bold;">{} Stock Bajo</span>','⚠')
        return format_html('<span style="color: green;">{} Stock OK</span>','✓')
    estado_stock.short_description = 'Estado'


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo_movimiento_badge', 'producto', 'cantidad', 'referencia', 'usuario', 'fecha')
    list_filter = ('tipo_movimiento', 'fecha', 'referencia')
    search_fields = ('producto__nombre', 'producto__codigo', 'referencia')
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'

    fieldsets = (
        ('Información del Movimiento', {
            'fields': ('producto', 'tipo_movimiento', 'cantidad', 'referencia')
        }),
        ('Usuario y Fecha', {
            'fields': ('usuario', 'fecha')
        }),
    )

    def tipo_movimiento_badge(self, obj):
        if obj.tipo_movimiento == 'ENTRADA':
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', '↑ ENTRADA')
        return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', '↓ SALIDA')
    tipo_movimiento_badge.short_description = 'Tipo'

    def save_model(self, request, obj, form, change):
        if not change:  # Si es un nuevo movimiento
            obj.usuario = request.user
        super().save_model(request, obj, form, change)