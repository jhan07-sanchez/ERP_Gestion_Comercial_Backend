from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, Rol, UsuarioRol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'descripcion', 'fecha_creacion')
    search_fields = ('nombre',)
    list_filter = ('fecha_creacion',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Información del Rol', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


class UsuarioRolInline(admin.TabularInline):
    model = UsuarioRol
    extra = 1
    verbose_name = 'Rol'
    verbose_name_plural = 'Roles del Usuario'


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'is_active', 'is_staff', 'fecha_creacion')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'fecha_creacion')
    search_fields = ('username', 'email')
    ordering = ('-fecha_creacion',)
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'last_login')
    inlines = [UsuarioRolInline]
    
    fieldsets = (
        ('Credenciales', {
            'fields': ('username', 'email', 'password')
        }),
        ('Información Personal', {
            'fields': ('token',)
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Fechas Importantes', {
            'fields': ('last_login', 'fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        ('Crear Nuevo Usuario', {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_active', 'is_staff'),
        }),
    )


@admin.register(UsuarioRol)
class UsuarioRolAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'rol')
    list_filter = ('rol',)
    search_fields = ('usuario__username', 'usuario__email', 'rol__nombre')
    autocomplete_fields = ['usuario']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('usuario', 'rol')
