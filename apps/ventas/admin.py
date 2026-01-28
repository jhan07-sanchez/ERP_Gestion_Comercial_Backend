# apps/ventas/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Venta, DetalleVenta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 1
    readonly_fields = ('subtotal',)
    fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('producto')


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'total_formateado', 'estado_badge', 'usuario', 'fecha')
    list_filter = ('estado', 'fecha')
    search_fields = ('cliente__nombre', 'cliente__documento')
    readonly_fields = ('fecha',)
    date_hierarchy = 'fecha'
    inlines = [DetalleVentaInline]
    
    fieldsets = (
        ('Información de la Venta', {
            'fields': ('cliente', 'total', 'estado')
        }),
        ('Usuario y Fecha', {
            'fields': ('usuario', 'fecha')
        }),
    )
    
    def total_formateado(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${:,.2f}</span>', obj.total)
    total_formateado.short_description = 'Total'
    
    def estado_badge(self, obj):
        colores = {
            'PENDIENTE': '#ffc107',
            'COMPLETADA': '#28a745',
            'CANCELADA': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            colores.get(obj.estado, '#6c757d'),
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def save_model(self, request, obj, form, change):
        if not change:  # Si es una nueva venta
            obj.usuario = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['marcar_como_completada', 'marcar_como_cancelada']
    
    def marcar_como_completada(self, request, queryset):
        updated = queryset.update(estado='COMPLETADA')
        self.message_user(request, f'{updated} venta(s) marcada(s) como completada(s).')
    marcar_como_completada.short_description = "Marcar como completada"
    
    def marcar_como_cancelada(self, request, queryset):
        updated = queryset.update(estado='CANCELADA')
        self.message_user(request, f'{updated} venta(s) marcada(s) como cancelada(s).')
    marcar_como_cancelada.short_description = "Marcar como cancelada"


@admin.register(DetalleVenta)
class DetalleVentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'venta', 'producto', 'cantidad', 'precio_unitario', 'subtotal_formateado')
    list_filter = ('venta__fecha',)
    search_fields = ('producto__nombre', 'venta__id')
    readonly_fields = ('subtotal',)
    
    def subtotal_formateado(self, obj):
        return format_html('<span style="color: green; font-weight: bold;">${:,.2f}</span>', obj.subtotal)
    subtotal_formateado.short_description = 'Subtotal'