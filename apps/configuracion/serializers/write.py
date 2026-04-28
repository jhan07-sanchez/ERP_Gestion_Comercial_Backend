# apps/configuracion/serializers/write.py
"""
Serializers de ESCRITURA para Configuración

Estos serializers se usan para validar y guardar datos (POST, PUT, PATCH).

¿Por qué están separados de los de lectura?
- Validaciones específicas para escritura (campos requeridos, formatos)
- Evitar que el usuario modifique campos de solo lectura
- Mayor control sobre qué puede cambiar el usuario
- Los consecutivos y fechas no se deben modificar directamente por la API

Autor: Sistema ERP
"""

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.configuracion.models import ConfiguracionGeneral


class ConfiguracionUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR la configuración general.

    Usado en:
    - PUT /api/configuracion/{id}/    → Actualización completa
    - PATCH /api/configuracion/{id}/  → Actualización parcial

    Campos NO editables (excluidos intencionalmente):
    - id, fecha_creacion, fecha_actualizacion (automáticos)
    - consecutivo_factura, consecutivo_compra, consecutivo_recibo
      (estos solo se modifican internamente al crear documentos)

    ¿Por qué los consecutivos no son editables aquí?
    - Para evitar errores: si alguien cambia el consecutivo manualmente,
      podría generar facturas duplicadas.
    - Los consecutivos se gestionan a través de endpoints dedicados.
    """

    class Meta:
        model = ConfiguracionGeneral
        fields = [
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
            # Fiscal
            "regimen_fiscal",
            "impuesto_porcentaje",
            "aplicar_impuesto_por_defecto",
            "moneda",
            "simbolo_moneda",
            "decimales_precio",
            # Numeración (solo prefijos y dígitos, no consecutivos)
            "prefijo_factura",
            "prefijo_compra",
            "prefijo_recibo",
            "digitos_consecutivo",
            # Inventario
            "stock_minimo_global",
            "alertar_stock_bajo",
            # Ventas
            "permitir_descuentos",
            "descuento_maximo",
            "permitir_venta_sin_stock",
            "terminos_condiciones",
        ]

    # ── Validaciones de campos individuales ───────────────────────────────────

    def validate_nombre_empresa(self, value):
        """
        Valida que el nombre no esté vacío ni sea muy corto.

        ¿Por qué validar aquí y no solo con el modelo?
        El modelo solo valida max_length. Aquí podemos dar mensajes más claros.
        """
        if len(value.strip()) < 2:
            raise serializers.ValidationError(
                "El nombre de la empresa debe tener al menos 2 caracteres."
            )
        return value.strip()

    def validate_nit(self, value):
        """Elimina espacios del NIT y valida que no esté vacío."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El NIT es requerido.")
        return value

    def validate_impuesto_porcentaje(self, value):
        """
        Valida que el impuesto esté entre 0% y 100%.
        Aunque el modelo tiene validators, aquí damos mensajes más claros.
        """
        if value < 0 or value > 100:
            raise serializers.ValidationError("El impuesto debe estar entre 0% y 100%.")
        return value

    def validate_descuento_maximo(self, value):
        """Valida que el descuento máximo sea entre 0% y 100%."""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                "El descuento máximo debe estar entre 0% y 100%."
            )
        return value

    def validate_prefijo_factura(self, value):
        """
        Valida el prefijo de factura:
        - Sin espacios (podría romper los números generados)
        - Solo letras y números
        - Máximo 10 caracteres (ya definido en el modelo)
        """
        value = value.strip().upper()
        if not value.isalnum():
            raise serializers.ValidationError(
                "El prefijo solo puede contener letras y números, sin espacios ni caracteres especiales."
            )
        return value

    def validate_prefijo_compra(self, value):
        """Misma validación que prefijo_factura."""
        value = value.strip().upper()
        if not value.isalnum():
            raise serializers.ValidationError(
                "El prefijo solo puede contener letras y números."
            )
        return value

    def validate_prefijo_recibo(self, value):
        """Misma validación que prefijo_factura."""
        value = value.strip().upper()
        if not value.isalnum():
            raise serializers.ValidationError(
                "El prefijo solo puede contener letras y números."
            )
        return value

    def validate(self, data):
        """
        Validaciones a nivel de objeto (usando múltiples campos).

        ¿Cuándo usar validate() vs validate_campo()?
        - validate_campo(): cuando la validación solo depende de ese campo.
        - validate(): cuando la validación depende de dos o más campos juntos.

        Ejemplo aquí:
        - Si permitir_descuentos=False, el descuento_maximo no importa.
        - Si permitir_descuentos=True, el descuento_maximo debe ser > 0.
        """
        permitir = data.get("permitir_descuentos", None)
        descuento = data.get("descuento_maximo", None)

        # Solo validar si ambos vienen

        if permitir is not None and descuento is not None:
            if permitir and descuento == 0:
                raise serializers.ValidationError(
                    {
                        "descuento_maximo": (
                            "Si se permiten descuentos, el descuento máximo debe ser mayor que 0%."
                        )
                    }
                )

        return data


class ResetConsecutivoSerializer(serializers.Serializer):
    """
    Serializer para resetear o ajustar un consecutivo de documentos.

    Usado en:
    - POST /api/configuracion/reset-consecutivo/

    ¿Por qué existe este endpoint separado?
    - Los consecutivos son datos críticos y sensibles.
    - Solo el Administrador puede modificarlos.
    - Se requiere confirmación explícita del tipo de documento.
    - Se registra el cambio en el log de auditoría.

    Ejemplo de uso:
        {
            "tipo": "factura",
            "nuevo_consecutivo": 1,
            "confirmar": true
        }
    """

    TIPO_CHOICES = [
        ("factura", "Factura de venta"),
        ("compra", "Compra"),
        ("recibo", "Recibo POS"),
    ]

    tipo = serializers.ChoiceField(
        choices=TIPO_CHOICES,
        required=True,
        help_text="Tipo de documento cuyo consecutivo se va a resetear",
    )

    nuevo_consecutivo = serializers.IntegerField(
        min_value=1,
        required=True,
        help_text="Nuevo valor del consecutivo (mínimo 1)",
    )

    confirmar = serializers.BooleanField(
        required=True,
        help_text="Debe ser true para confirmar el cambio. Esto no puede deshacerse.",
    )

    def validate_confirmar(self, value):
        """El usuario DEBE confirmar explícitamente."""
        if not value:
            raise serializers.ValidationError(
                "Debe confirmar el cambio enviando confirmar=true. "
                "Esta acción no se puede deshacer."
            )
        return value
