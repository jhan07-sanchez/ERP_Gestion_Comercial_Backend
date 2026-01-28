# apps/configuracion/admin.py
from django.contrib import admin
from .models import ConfiguracionGeneral

@admin.register(ConfiguracionGeneral)
class ConfiguracionGeneralAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'nit', 'telefono', 'moneda')
