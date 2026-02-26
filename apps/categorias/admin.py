# apps/categorias/admin.py
from django.contrib import admin
from apps.categorias.models import Categoria


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'total_productos', 'fecha_creacion')
    search_fields = ('nombre',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Información de la Categoría', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )

    def total_productos(self, obj):
        return obj.productos.count()
    total_productos.short_description = 'Total Productos'
