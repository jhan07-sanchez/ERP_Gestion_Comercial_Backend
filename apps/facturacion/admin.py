from django.contrib import admin
from .models import (
    Factura,
    FacturaDetalle,
    FacturaImpuesto,
    PagoFactura,
    HistorialFactura,
    NotaCredito,
    NotaCreditoDetalle,
    NotaDebito,
    NotaDebitoDetalle
)


class FacturaDetalleInline(admin.TabularInline):
    model = FacturaDetalle
    extra = 0
    readonly_fields = ('subtotal', 'impuestos_linea', 'total_linea')


class FacturaImpuestoInline(admin.TabularInline):
    model = FacturaImpuesto
    extra = 0


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'cliente', 'estado', 'total', 'saldo_pendiente', 'fecha_emision', 'fecha_creacion')
    list_filter = ('estado', 'fecha_emision')
    search_fields = ('numero', 'cliente__nombre', 'cliente__numero_documento')
    inlines = [FacturaDetalleInline, FacturaImpuestoInline]
    readonly_fields = ('subtotal', 'descuento_total', 'impuestos_total', 'total', 'saldo_pendiente')


@admin.register(PagoFactura)
class PagoFacturaAdmin(admin.ModelAdmin):
    list_display = ('factura', 'metodo_pago', 'monto', 'fecha', 'registrado_por')
    list_filter = ('metodo_pago', 'fecha')
    search_fields = ('factura__numero', 'referencia')


@admin.register(HistorialFactura)
class HistorialFacturaAdmin(admin.ModelAdmin):
    list_display = ('factura', 'accion', 'usuario', 'fecha')
    list_filter = ('accion', 'fecha')
    search_fields = ('factura__numero', 'accion')

admin.site.register(NotaCredito)
admin.site.register(NotaCreditoDetalle)
admin.site.register(NotaDebito)
admin.site.register(NotaDebitoDetalle)
