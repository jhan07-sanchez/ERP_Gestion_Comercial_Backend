# apps/configuracion/serializers/read.py
"""
Serializers de LECTURA para Configuración

Estos serializers se usan en las respuestas GET.
Muestran los datos de forma legible y completa.

¿Por qué serializers de lectura separados?
- En la respuesta queremos: nombre del régimen en texto ("Régimen Común")
- En el envío recibimos: el código ("COMUN")
- Podemos agregar campos calculados que no existen en el modelo
- Podemos incluir campos de solo lectura sin riesgo de edición

Autor: Sistema ERP
"""

from rest_framework import serializers
from apps.configuracion.models import ConfiguracionGeneral, Impuesto, MetodoPago, CondicionPago
from apps.configuracion.services.configuracion_service import ConfiguracionService


class ImpuestoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Impuesto
        fields = ["id", "nombre", "porcentaje", "activo"]

class MetodoPagoSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    class Meta:
        model = MetodoPago
        fields = ["id", "nombre", "activo", "es_efectivo", "tipo", "tipo_display"]

class CondicionPagoSerializer(serializers.ModelSerializer):
    es_contado = serializers.BooleanField(read_only=True)
    class Meta:
        model = CondicionPago
        fields = ["id", "nombre", "dias_plazo", "activo", "es_contado"]

class ConfiguracionReadSerializer(serializers.ModelSerializer):
    """
    Serializer de LECTURA completo de la configuración.

    Usado en:
    - GET /api/configuracion/          → Ver la configuración actual
    - Cualquier endpoint que necesite mostrar la config

    Campos especiales:
    - regimen_fiscal_display: muestra el nombre legible (ej: "Régimen Común")
    - moneda_display: muestra el nombre legible (ej: "Peso Colombiano (COP)")
    - logo_url: URL completa del logo (si existe)
    - numero_factura_preview: vista previa del próximo número de factura
    """

    # Campos con nombre legible (display) de los choices
    regimen_fiscal_display = serializers.CharField(
        source="get_regimen_fiscal_display",
        read_only=True,
    )

    moneda_display = serializers.CharField(
        source="get_moneda_display",
        read_only=True,
    )

    # Logo como URL completa
    logo_url = serializers.SerializerMethodField()

    # Vista previa de próximos números
    numero_factura_preview = serializers.SerializerMethodField()
    numero_compra_preview = serializers.SerializerMethodField()
    numero_recibo_preview = serializers.SerializerMethodField()

    # Master payload fields
    impuestos_activos = serializers.SerializerMethodField()
    metodos_pago_activos = serializers.SerializerMethodField()
    condiciones_pago_activas = serializers.SerializerMethodField()

    class Meta:
        model = ConfiguracionGeneral
        fields = [
            # Identificación
            "id",
            # Datos empresa
            "nombre_empresa",
            "razon_social",
            "nit",
            "telefono",
            "telefono_secundario",
            "email",
            "sitio_web",
            "direccion",
            "ciudad",
            "departamento",
            "pais",
            "logo",
            "logo_url",
            # Fiscal
            "regimen_fiscal",
            "regimen_fiscal_display",
            "impuesto_porcentaje",
            "aplicar_impuesto_por_defecto",
            "moneda",
            "moneda_display",
            "simbolo_moneda",
            "decimales_precio",
            # Numeración
            "prefijo_factura",
            "consecutivo_factura",
            "prefijo_compra",
            "consecutivo_compra",
            "prefijo_recibo",
            "consecutivo_recibo",
            "digitos_consecutivo",
            "numero_factura_preview",
            "numero_compra_preview",
            "numero_recibo_preview",
            # Inventario
            "stock_minimo_global",
            "alertar_stock_bajo",
            # Ventas
            "permitir_descuentos",
            "descuento_maximo",
            "permitir_venta_sin_stock",
            "terminos_condiciones",
            # Resolución DIAN
            "numero_resolucion_factura",
            "rango_inicial_factura",
            "rango_final_factura",
            "fecha_inicio_resolucion",
            "fecha_fin_resolucion",
            # Plantillas
            "plantilla_factura_pdf",
            "plantilla_correo_factura",
            # Contabilidad
            "cuenta_ventas",
            "cuenta_impuestos",
            "cuenta_cxc_clientes",
            # Master Payload
            "impuestos_activos",
            "metodos_pago_activos",
            "condiciones_pago_activas",
            # Metadata
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_logo_url(self, obj):
        """
        Retorna la URL completa del logo.
        Si no hay logo, retorna None.

        ¿Por qué usamos SerializerMethodField en vez de solo 'logo'?
        Porque el campo logo del modelo retorna solo la ruta relativa.
        Con este método retornamos la URL completa con el dominio.
        """
        if obj.logo:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None

    def get_numero_factura_preview(self, obj):
        """
        Vista previa del próximo número de factura (sin incrementar el consecutivo).
        Solo es informativo para mostrar en la interfaz.

        Ejemplo: Si prefijo="FAC", consecutivo=5, digitos=4 → "FAC-0005"
        """
        return f"{obj.prefijo_factura}-{str(obj.consecutivo_factura).zfill(obj.digitos_consecutivo)}"

    def get_numero_compra_preview(self, obj):
        """Vista previa del próximo número de compra."""
        return f"{obj.prefijo_compra}-{str(obj.consecutivo_compra).zfill(obj.digitos_consecutivo)}"

    def get_numero_recibo_preview(self, obj):
        """Vista previa del próximo número de recibo."""
        return f"{obj.prefijo_recibo}-{str(obj.consecutivo_recibo).zfill(obj.digitos_consecutivo)}"

    def get_impuestos_activos(self, obj):
        return ImpuestoSerializer(ConfiguracionService.obtener_impuestos_activos(), many=True).data

    def get_metodos_pago_activos(self, obj):
        return MetodoPagoSerializer(ConfiguracionService.obtener_metodos_pago_activos(), many=True).data

    def get_condiciones_pago_activas(self, obj):
        return CondicionPagoSerializer(ConfiguracionService.obtener_condiciones_pago_activas(), many=True).data


class ConfiguracionResumenSerializer(serializers.ModelSerializer):
    """
    Serializer RESUMIDO para usar en otras partes del sistema.

    Usado en:
    - Dashboard (para mostrar nombre empresa y moneda)
    - Headers de facturas/reportes
    - Cualquier app que necesite solo los datos básicos de la empresa

    ¿Por qué tener uno resumido?
    - Evita transferir datos innecesarios cuando solo necesitas el nombre o moneda
    - Más eficiente en APIs que lo incluyen como dato anidado
    """

    class Meta:
        model = ConfiguracionGeneral
        fields = [
            "nombre_empresa",
            "nit",
            "telefono",
            "email",
            "moneda",
            "simbolo_moneda",
            "impuesto_porcentaje",
        ]
