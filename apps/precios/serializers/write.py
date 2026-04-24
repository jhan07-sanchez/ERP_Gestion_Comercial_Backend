# apps/precio/serializers/write.py
"""
SERIALIZERS DE ESCRITURA para la app Precio

¿Qué es un serializer de ESCRITURA?
─────────────────────────────────────
Cuando alguien hace POST /api/precios/ (crear) o PATCH /api/precios/1/
(actualizar), el serializer de escritura:

1. RECIBE los datos JSON del frontend
2. VALIDA cada campo (tipos, rangos, unicidad, etc.)
3. Si todo está OK, guarda en la DB
4. Si hay error, retorna mensajes claros de qué falló

¿Cómo funciona la validación en DRF?
──────────────────────────────────────
Hay 3 niveles de validación (en orden de ejecución):

Nivel 1 - Por campo:
    def validate_precio(self, value):
        # Se ejecuta SOLO para el campo 'precio'
        if value <= 0:
            raise serializers.ValidationError("...")
        return value

Nivel 2 - Cruzada (varios campos juntos):
    def validate(self, data):
        # Se ejecuta al FINAL con todos los datos ya validados
        if data['fecha_fin'] < data['fecha_inicio']:
            raise serializers.ValidationError("...")
        return data

Nivel 3 - Modelo (validators del modelo):
    # Django llama automáticamente a model.full_clean()
"""

from rest_framework import serializers
from django.utils import timezone
from apps.precios.models import ListaPrecioCompra


# ============================================================================
# SERIALIZER PARA CREAR un nuevo precio
# ============================================================================


class ListaPrecioCompraCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR un nuevo precio de compra.

    Usado en: POST /api/precios/

    Proceso:
    1. Recibe: producto_id, proveedor_id, precio, fecha_inicio (opcional)
    2. Valida que el producto exista y esté activo
    3. Valida que el proveedor exista y esté activo
    4. Valida que el precio sea mayor a 0
    5. Si ya existe un precio vigente para este par, lo desactiva (historial)
    6. Crea el nuevo precio como vigente

    NOTA: El paso 4 y 5 se hacen en el SERVICE, no aquí.
    El serializer SOLO valida datos. El servicio hace la lógica de negocio.
    """

    class Meta:
        model = ListaPrecioCompra
        fields = [
            "producto",
            "proveedor",
            "precio",
            "fecha_inicio",
        ]

    def validate_producto(self, value):
        """
        Validar que el producto exista y esté activo.

        ¿Por qué no usamos solo ForeignKey validation?
        DRF ya valida que el ID exista, pero no valida si está activo.
        Nosotros añadimos esa regla de negocio aquí.
        """
        if not value.estado:
            raise serializers.ValidationError(
                f"El producto '{value.nombre}' está inactivo. "
                f"Solo se pueden crear precios para productos activos."
            )
        return value

    def validate_proveedor(self, value):
        """Validar que el proveedor exista y esté activo."""
        if not value.estado:
            raise serializers.ValidationError(
                f"El proveedor '{value.nombre}' está inactivo. "
                f"Solo se pueden crear precios para proveedores activos."
            )
        return value

    def validate_precio(self, value):
        """
        Validar que el precio sea razonable.

        ¿Por qué DecimalField y no FloatField para dinero?
        Float tiene problemas de precisión: 0.1 + 0.2 = 0.30000000000000004
        Decimal es exacto. Para precios siempre usa Decimal.
        """
        if value <= 0:
            raise serializers.ValidationError(
                "El precio debe ser mayor a $0. "
                "Si el producto es gratuito, registra un precio de $0.01."
            )

        if value > 999_999_999:
            raise serializers.ValidationError(
                "El precio parece demasiado alto. Verifica el valor ingresado."
            )

        return value

    def validate_fecha_inicio(self, value):
        """
        Validar la fecha de inicio.

        Permitimos fechas un poco en el futuro (hasta 30 días)
        para precios pre-acordados con proveedores.
        """
        ahora = timezone.now()

        # No permitir fechas muy antiguas (más de 2 años)
        hace_dos_anios = ahora.replace(year=ahora.year - 2)
        if value < hace_dos_anios:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser anterior a 2 años."
            )

        return value

    def validate(self, data):
        """
        Validación CRUZADA: usa múltiples campos juntos.

        Aquí verificamos que no exista ya un precio IDÉNTICO vigente.
        La diferencia con la UniqueConstraint de la DB:
        - La DB bloquea duplicados en el nivel de datos.
        - Esta validación da un mensaje de error AMIGABLE al usuario
          ANTES de intentar guardar en la DB.
        """
        producto = data.get("producto")
        proveedor = data.get("proveedor")
        precio_nuevo = data.get("precio")

        if producto and proveedor:
            precio_vigente = ListaPrecioCompra.objects.filter(
                producto=producto,
                proveedor=proveedor,
                vigente=True,
            ).first()

            if precio_vigente:
                # Si el precio es idéntico, informamos al usuario
                if precio_vigente.precio == precio_nuevo:
                    raise serializers.ValidationError(
                        {
                            "precio": (
                                f"Ya existe un precio vigente de ${precio_vigente.precio} "
                                f"para este producto y proveedor. "
                                f"El nuevo precio es igual al actual."
                            )
                        }
                    )
                # Si es diferente, está bien — el servicio hará la transición

        return data


# ============================================================================
# SERIALIZER PARA ACTUALIZAR un precio existente
# ============================================================================


class ListaPrecioCompraUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR un precio existente.

    Usado en: PUT/PATCH /api/precios/{id}/

    IMPORTANTE: No se permite cambiar producto ni proveedor.
    Si cambia la combinación producto+proveedor, es un NUEVO precio,
    no una actualización del existente.

    Solo se puede cambiar: precio, fecha_inicio, fecha_fin.
    """

    # read_only=True: este campo se muestra en la respuesta
    # pero NO se puede modificar desde la petición.
    # Es como hacer el campo "solo lectura" en la edición.
    producto = serializers.PrimaryKeyRelatedField(read_only=True)
    proveedor = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ListaPrecioCompra
        fields = [
            "producto",  # read_only
            "proveedor",  # read_only
            "precio",
            "fecha_inicio",
            "fecha_fin",
        ]

    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a $0.")
        if value > 999_999_999:
            raise serializers.ValidationError("El precio parece demasiado alto.")
        return value

    def validate(self, data):
        """
        Validar que fecha_fin sea posterior a fecha_inicio.

        self.instance es el OBJETO ACTUAL en la DB (antes de actualizar).
        Esto nos permite comparar el valor nuevo con el actual.
        """
        # Obtener fecha_inicio: la nueva (si se envió) o la actual del objeto
        fecha_inicio = data.get(
            "fecha_inicio", self.instance.fecha_inicio if self.instance else None
        )
        fecha_fin = data.get("fecha_fin")

        if fecha_inicio and fecha_fin:
            if fecha_fin <= fecha_inicio:
                raise serializers.ValidationError(
                    {
                        "fecha_fin": (
                            f"La fecha de fin ({fecha_fin}) debe ser posterior "
                            f"a la fecha de inicio ({fecha_inicio})."
                        )
                    }
                )

        # No se puede "reactivar" un precio histórico
        if self.instance and not self.instance.vigente:
            campos_no_permitidos = [k for k in data.keys() if k not in ["fecha_fin"]]
            if campos_no_permitidos:
                raise serializers.ValidationError(
                    "No se puede modificar un precio histórico. "
                    "Crea un nuevo precio vigente en su lugar."
                )

        return data
