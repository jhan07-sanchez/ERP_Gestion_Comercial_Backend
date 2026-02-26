# apps/configuracion/admin.py
"""
Administrador Django para la app Configuración

¿Para qué sirve el Admin de Django?
- Interfaz web automática para gestionar los modelos
- Accesible en /admin/ (solo superusuarios)
- Muy útil para configuración inicial del sistema y debugging

Personalizamos el admin para:
- Mostrar los campos agrupados por sección (más organizado)
- Control de qué campos son editables
- Vista más profesional

Autor: Sistema ERP
"""

from django.contrib import admin
from apps.configuracion.models import ConfiguracionGeneral


@admin.register(ConfiguracionGeneral)
class ConfiguracionGeneralAdmin(admin.ModelAdmin):
    """
    Admin personalizado para ConfiguracionGeneral.

    fieldsets agrupa los campos por secciones.
    Cada tupla es: ("Nombre de sección", {"fields": [lista de campos]})
    """

    # Columnas en la lista del admin
    list_display = (
        "nombre_empresa",
        "nit",
        "telefono",
        "moneda",
        "impuesto_porcentaje",
        "fecha_actualizacion",
    )

    # Campos de solo lectura (no editables desde el admin)
    readonly_fields = ("fecha_creacion", "fecha_actualizacion")

    # Organización de campos en secciones
    fieldsets = (
        # ── Sección 1: Datos de la empresa ─────────────────────────────────
        (
            "🏢 Datos de la Empresa",
            {
                "fields": (
                    "nombre_empresa",
                    "razon_social",
                    "nit",
                    "logo",
                    "telefono",
                    "telefono_secundario",
                    "email",
                    "sitio_web",
                    "direccion",
                    "ciudad",
                    "departamento",
                    "pais",
                ),
            },
        ),
        # ── Sección 2: Configuración fiscal ────────────────────────────────
        (
            "💰 Configuración Fiscal",
            {
                "fields": (
                    "regimen_fiscal",
                    "impuesto_porcentaje",
                    "aplicar_impuesto_por_defecto",
                    "moneda",
                    "simbolo_moneda",
                    "decimales_precio",
                ),
            },
        ),
        # ── Sección 3: Numeración de documentos ────────────────────────────
        (
            "🔢 Numeración de Documentos",
            {
                "fields": (
                    "prefijo_factura",
                    "consecutivo_factura",
                    "prefijo_compra",
                    "consecutivo_compra",
                    "prefijo_recibo",
                    "consecutivo_recibo",
                    "digitos_consecutivo",
                ),
                # 'description' agrega texto de ayuda arriba de la sección
                "description": (
                    "⚠️ Tenga cuidado al modificar los consecutivos. "
                    "Cambiarlos puede generar documentos con números duplicados."
                ),
            },
        ),
        # ── Sección 4: Inventario ───────────────────────────────────────────
        (
            "📦 Configuración de Inventario",
            {
                "fields": (
                    "stock_minimo_global",
                    "alertar_stock_bajo",
                ),
            },
        ),
        # ── Sección 5: Ventas ───────────────────────────────────────────────
        (
            "🛒 Configuración de Ventas",
            {
                "fields": (
                    "permitir_descuentos",
                    "descuento_maximo",
                    "permitir_venta_sin_stock",
                    "terminos_condiciones",
                ),
            },
        ),
        # ── Sección 6: Metadata ─────────────────────────────────────────────
        (
            "📋 Información del registro",
            {
                "fields": ("fecha_creacion", "fecha_actualizacion"),
                "classes": ("collapse",),  # Colapsable por defecto
            },
        ),
    )

    def has_add_permission(self, request):
        """
        Deshabilita el botón "Agregar" si ya existe un registro.

        ¿Por qué?
        La configuración es un Singleton: solo puede haber UN registro.
        Si el usuario intenta crear otro, el modelo lanzaría un error.
        Mejor prevenir desde el admin.
        """
        return not ConfiguracionGeneral.objects.exists()

    def has_delete_permission(self, request, obj=None):
        """
        Deshabilita la eliminación de la configuración.

        El sistema ERP no puede funcionar sin configuración.
        Si se elimina, muchas funciones fallarían.
        Mejor no permitirlo desde el admin.
        """
        return False
