from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, Rol, UsuarioRol, Empresa, Suscripcion, SolicitudCuenta, Modulo, Plan
from .services.saas_service import SaaSAccountService


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


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'fecha_creacion')
    search_fields = ('nombre',)


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'codigo', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre', 'codigo')
    prepopulated_fields = {'codigo': ('nombre',)}


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'precio', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'fecha_creacion')
    search_fields = ('nombre',)
    filter_horizontal = ('modulos',)


@admin.register(Suscripcion)
class SuscripcionAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'plan', 'estado_pago', 'fecha_inicio', 'fecha_fin', 'activa', 'es_trial')
    list_filter = ('activa', 'es_trial', 'estado_pago', 'plan')
    search_fields = ('empresa__nombre', 'stripe_customer_id', 'stripe_subscription_id')
    fieldsets = (
        ('Información Básica', {
            'fields': ('empresa', 'plan', 'activa', 'es_trial')
        }),
        ('Fechas', {
            'fields': ('fecha_inicio', 'fecha_fin')
        }),
        ('Stripe / Pagos', {
            'fields': ('estado_pago', 'stripe_customer_id', 'stripe_subscription_id'),
            'classes': ('collapse',),
        }),
    )


@admin.register(SolicitudCuenta)
class SolicitudCuentaAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'nombre', 'email', 'plan', 'estado', 'fecha_creacion')
    list_filter = ('estado', 'plan')
    search_fields = ('empresa', 'email', 'nombre')
    actions = ['aprobar_solicitudes']

    @admin.action(description='Aprobar solicitudes seleccionadas')
    def aprobar_solicitudes(self, request, queryset):
        solicitudes = queryset.filter(estado='PENDIENTE')
        contador = 0
        errores = 0
        
        for solicitud in solicitudes:
            try:
                SaaSAccountService.aprobar_solicitud(solicitud.id)
                contador += 1
            except Exception as e:
                self.message_user(request, f"Error en solicitud {solicitud.id}: {str(e)}", messages.ERROR)
                errores += 1
        
        if contador > 0:
            self.message_user(request, f"Se aprobaron {contador} solicitudes exitosamente.", messages.SUCCESS)
        if errores > 0:
            self.message_user(request, f"No se pudieron procesar {errores} solicitudes.", messages.WARNING)
        
        pendientes_restantes = queryset.exclude(estado='PENDIENTE').count()
        if pendientes_restantes > 0:
            self.message_user(request, f"{pendientes_restantes} solicitudes omitidas (no estaban pendientes).", messages.INFO)

