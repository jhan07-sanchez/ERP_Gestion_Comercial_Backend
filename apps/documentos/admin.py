# apps/documentos/admin.py
from django.contrib import admin
from apps.documentos.models import Documento, DocumentoDetalle, SecuenciaNumeracionDocumento


class DocumentoDetalleInline(admin.TabularInline):
    model = DocumentoDetalle
    extra = 0
    readonly_fields = ("orden", "descripcion", "producto_id", "cantidad", "precio_unitario", "subtotal")
    classes = ("collapse",)


@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = (
        "numero_interno",
        "tipo",
        "estado",
        "codigo_verificacion",
        "total",
        "fecha_emision",
    )
    list_filter = ("tipo", "estado", "fecha_emision")
    search_fields = ("numero_interno", "referencia_operacion", "uuid", "codigo_verificacion")
    readonly_fields = (
        "uuid", 
        "hash_verificacion", 
        "codigo_verificacion", 
        "numero_secuencia",
        "fecha_emision"
    )
    inlines = [DocumentoDetalleInline]
    
    fieldsets = (
        ("Identificación y Estado", {
            "fields": ("tipo", "estado", "numero_interno", "numero_secuencia", "referencia_operacion")
        }),
        ("Seguridad e Integridad", {
            "fields": ("uuid", "hash_verificacion", "codigo_verificacion"),
            "classes": ("collapse",),
        }),
        ("Relaciones", {
            "fields": ("venta", "compra", "usuario")
        }),
        ("Montos", {
            "fields": ("subtotal", "impuestos", "total")
        }),
        ("Fechas y Notas", {
            "fields": ("fecha_emision", "fecha_vencimiento", "notas")
        }),
    )


@admin.register(SecuenciaNumeracionDocumento)
class SecuenciaNumeracionDocumentoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "prefijo", "ultimo_numero")
    search_fields = ("codigo", "prefijo")
