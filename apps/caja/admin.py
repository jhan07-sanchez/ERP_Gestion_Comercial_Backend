# apps/caja/admin.py
from django.contrib import admin
from .models import MetodoPago, Caja, SesionCaja, MovimientoCaja, ArqueoCaja


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "es_efectivo", "activo", "fecha_creacion")
    list_editable = ("activo",)
    list_filter = ("activo", "es_efectivo")
    search_fields = ("nombre",)


@admin.register(Caja)
class CajaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "activa", "esta_abierta", "fecha_creacion")
    list_filter = ("activa",)
    search_fields = ("nombre",)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    def esta_abierta(self, obj):
        return obj.esta_abierta

    esta_abierta.boolean = True
    esta_abierta.short_description = "¿Abierta?"


class MovimientoCajaInline(admin.TabularInline):
    model = MovimientoCaja
    extra = 0
    readonly_fields = (
        "tipo",
        "monto",
        "descripcion",
        "metodo_pago",
        "usuario",
        "fecha",
    )
    can_delete = False


@admin.register(SesionCaja)
class SesionCajaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "caja",
        "usuario",
        "estado",
        "monto_inicial",
        "monto_final",
        "fecha_apertura",
        "fecha_cierre",
    )
    list_filter = ("estado", "caja")
    search_fields = ("usuario__username", "caja__nombre")
    readonly_fields = ("fecha_apertura",)
    inlines = [MovimientoCajaInline]


@admin.register(MovimientoCaja)
class MovimientoCajaAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "monto", "metodo_pago", "usuario", "fecha")
    list_filter = ("tipo", "metodo_pago", "sesion__caja")
    search_fields = ("descripcion", "usuario__username")
    readonly_fields = ("fecha",)


@admin.register(ArqueoCaja)
class ArqueoCajaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "sesion",
        "tipo",
        "monto_contado",
        "monto_esperado",
        "diferencia",
        "fecha",
    )
    list_filter = ("tipo",)
    readonly_fields = ("diferencia", "fecha")
