# apps/productos/admin.py
from django.contrib import admin
from django.utils.html import format_html
from apps.productos.models import Producto
from apps.inventario.models import Inventario


class InventarioInline(admin.StackedInline):
    model = Inventario
    extra = 0
    readonly_fields = ('stock_actual', 'fecha_actualizacion')
    can_delete = False


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('id', 'codigo', 'nombre', 'categoria', 'precio_venta', 'stock_actual_display', 'estado', 'estado_badge', 'imagen_preview')
    list_filter = ('estado', 'categoria', 'fecha_ingreso')
    search_fields = ('codigo', 'nombre', 'descripcion')
    list_editable = ('estado',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'imagen_preview')
    inlines = [InventarioInline]

    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'nombre', 'categoria', 'descripcion')
        }),
        ('Precios', {
            'fields': ('precio_compra', 'precio_venta')
        }),
        ('Inventario', {
            'fields': ('stock_minimo', 'fecha_ingreso')
        }),
        ('Imagen', {
            'fields': ('imagen', 'imagen_preview')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    def stock_actual_display(self, obj):
        try:
            stock = obj.inventario.stock_actual
            if stock <= obj.stock_minimo:
                return format_html('<span style="color: red; font-weight: bold;">{}</span>', stock)
            return stock
        except:
            return 0
    stock_actual_display.short_description = 'Stock Actual'

    def estado_badge(self, obj):
        if obj.estado:
            return format_html('<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', 'Activo')
        return format_html('<span style="background-color: #dc3545; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>', 'Inactivo')
    estado_badge.short_description = 'Estado'

    def imagen_preview(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="max-width: 200px; max-height: 200px;" />', obj.imagen.url)
        return "Sin imagen"
    imagen_preview.short_description = 'Vista Previa'

    actions = ['activar_productos', 'desactivar_productos']

    def activar_productos(self, request, queryset):
        updated = queryset.update(estado=True)
        self.message_user(request, f'{updated} producto(s) activado(s) exitosamente.')
    activar_productos.short_description = "Activar productos seleccionados"

    def desactivar_productos(self, request, queryset):
        updated = queryset.update(estado=False)
        self.message_user(request, f'{updated} producto(s) desactivado(s) exitosamente.')
    desactivar_productos.short_description = "Desactivar productos seleccionados"
