# apps/clientes/admin.py
from django.contrib import admin
from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'documento', 'telefono', 'email', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'fecha_creacion')
    search_fields = ('nombre', 'documento', 'email', 'telefono')
    list_editable = ('estado',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('nombre', 'documento')
        }),
        ('Información de Contacto', {
            'fields': ('telefono', 'email', 'direccion')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['activar_clientes', 'desactivar_clientes']
    
    def activar_clientes(self, request, queryset):
        updated = queryset.update(estado=True)
        self.message_user(request, f'{updated} cliente(s) activado(s) exitosamente.')
    activar_clientes.short_description = "Activar clientes seleccionados"
    
    def desactivar_clientes(self, request, queryset):
        updated = queryset.update(estado=False)
        self.message_user(request, f'{updated} cliente(s) desactivado(s) exitosamente.')
    desactivar_clientes.short_description = "Desactivar clientes seleccionados"