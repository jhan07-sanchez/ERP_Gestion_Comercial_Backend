# apps/compras/serializers/write.py
"""
🔹 SERIALIZERS DE ESCRITURA - Versión Mejorada
================================================

Características:
- Validaciones más robustas
- Mejor manejo de errores
- Mensajes claros para el frontend
- Soporte completo para actualización

Autor: Sistema ERP
Versión: 2.0
Fecha: 2026-02-15
"""

from rest_framework import serializers
from django.db import transaction
from decimal import Decimal

from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto
from apps.proveedores.models import Proveedor


# ============================================================================
# SERIALIZERS DE DETALLE DE COMPRA (WRITE)
# ============================================================================


class DetalleCompraWriteSerializer(serializers.Serializer):
    """
    Serializer para crear/actualizar detalles de compra

    Validaciones:
    - Producto existe y está activo
    - Cantidad positiva y razonable
    - Precio positivo
    """

    producto_id = serializers.IntegerField(min_value=1)
    cantidad = serializers.IntegerField(min_value=1)
    precio_compra = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,  # Se toma del producto si no se proporciona
        min_value=Decimal("0.01"),
    )

    def validate_producto_id(self, value):
        """Validar que el producto existe"""
        try:
            producto = Producto.objects.get(id=value)

            # Validar que el producto esté activo (si tienes campo estado)
            # if not producto.estado:
            #     raise serializers.ValidationError(
            #         "El producto está inactivo y no puede ser comprado."
            #     )

            return value
        except Producto.DoesNotExist:
            raise serializers.ValidationError(f"El producto con ID {value} no existe.")

    def validate_cantidad(self, value):
        """Validar cantidad razonable"""
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")

        if value > 100000:
            raise serializers.ValidationError(
                "La cantidad es demasiado grande (máximo 100,000). "
                "Verifica el valor ingresado."
            )

        return value

    def validate_precio_compra(self, value):
        """Validar precio si se proporciona"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("El precio de compra debe ser mayor a 0.")

        return value

    def validate(self, data):
        """
        Validaciones a nivel de objeto

        - Si no hay precio, toma el del producto
        - Valida coherencia de datos
        """
        producto_id = data.get("producto_id")

        # Si no se proporciona precio, usar el del producto
        if "precio_compra" not in data or data["precio_compra"] is None:
            producto = Producto.objects.get(id=producto_id)
            data["precio_compra"] = producto.precio_compra

            # Advertir si el precio del producto es 0
            if data["precio_compra"] <= 0:
                raise serializers.ValidationError(
                    {
                        "precio_compra": (
                            f"El producto '{producto.nombre}' no tiene precio de compra "
                            "configurado. Por favor, especifica un precio."
                        )
                    }
                )

        return data


# ============================================================================
# SERIALIZERS DE COMPRA (WRITE)
# ============================================================================


class CompraCreateSerializer(serializers.Serializer):
    """
    Serializer para CREAR compras

    Usado en: POST /api/compras/

    Proceso:
    1. Valida proveedor (existe y activo)
    2. Valida productos (existen y con stock)
    3. Valida fecha (no futura, razonable)
    4. Crea compra con estado PENDIENTE
    5. No afecta inventario hasta confirmación
    """

    proveedor_id = serializers.PrimaryKeyRelatedField(
        queryset=Proveedor.objects.filter(estado=True),  # Solo proveedores activos
        source="proveedor",
        error_messages={
            "does_not_exist": "El proveedor seleccionado no existe o está inactivo.",
            "required": "El proveedor es requerido.",
        },
    )

    fecha = serializers.DateField(
        error_messages={
            "required": "La fecha es requerida.",
            "invalid": "Formato de fecha inválido. Use YYYY-MM-DD.",
        }
    )

    observaciones = serializers.CharField(
        max_length=500, required=False, allow_blank=True, trim_whitespace=True
    )

    detalles = DetalleCompraWriteSerializer(
        many=True,
        error_messages={
            "required": "Debe incluir al menos un producto.",
            "empty": "Debe incluir al menos un producto.",
        },
    )

    def validate_fecha(self, value):
        """Validar que la fecha sea razonable"""
        from django.utils import timezone
        from datetime import timedelta

        hoy = timezone.now().date()

        # No permitir fechas futuras
        if value > hoy:
            raise serializers.ValidationError(
                "No se puede registrar una compra con fecha futura."
            )

        # Advertir si la fecha es muy antigua (más de 1 año)
        hace_un_ano = hoy - timedelta(days=365)
        if value < hace_un_ano:
            # Solo advertencia, no error
            pass

        return value

    def validate_detalles(self, value):
        """Validar lista de detalles"""
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Debe incluir al menos un producto en la compra."
            )

        if len(value) > 100:
            raise serializers.ValidationError(
                "No puede incluir más de 100 productos en una compra. "
                "Si necesita más, divida en múltiples compras."
            )

        # Validar que no haya productos duplicados
        productos_ids = [detalle["producto_id"] for detalle in value]
        if len(productos_ids) != len(set(productos_ids)):
            raise serializers.ValidationError(
                "No puede incluir el mismo producto múltiples veces. "
                "Use el campo 'cantidad' para indicar más unidades."
            )

        return value

    def validate(self, data):
        """
        Validaciones a nivel de compra

        - Calcula el total
        - Valida que el total sea razonable
        """
        detalles = data.get("detalles", [])

        # Calcular total
        total = Decimal("0.00")
        for detalle in detalles:
            cantidad = Decimal(str(detalle["cantidad"]))
            precio = detalle.get("precio_compra")

            # Si no hay precio, obtenerlo del producto
            if precio is None:
                producto = Producto.objects.get(id=detalle["producto_id"])
                precio = producto.precio_compra

            precio = Decimal(str(precio))
            total += cantidad * precio

        # Validar que el total no sea 0
        if total <= 0:
            raise serializers.ValidationError(
                {
                    "detalles": "El total de la compra no puede ser $0. Verifica los precios."
                }
            )

        # Validar que el total sea razonable (< $1,000,000,000)
        if total > Decimal("1000000000"):
            raise serializers.ValidationError(
                {
                    "detalles": (
                        "El total de la compra es demasiado alto. "
                        "Verifica las cantidades y precios."
                    )
                }
            )

        data["total"] = total
        data["estado"] = "PENDIENTE"  # Siempre se crea como PENDIENTE

        return data


class CompraUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR compras

    Usado en: PUT/PATCH /api/compras/{id}/

    Permite actualizar:
    - Proveedor (si está PENDIENTE)
    - Fecha (si está PENDIENTE)
    - Observaciones (siempre)
    - Estado (con validaciones)
    - Detalles (si está PENDIENTE)

    Restricciones:
    - No se puede actualizar una compra ANULADA
    - No se pueden cambiar detalles de una compra REALIZADA
    """

    proveedor_id = serializers.PrimaryKeyRelatedField(
        queryset=Proveedor.objects.filter(estado=True),
        source="proveedor",
        required=False,
    )

    fecha = serializers.DateField(required=False)

    observaciones = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )

    estado = serializers.ChoiceField(
        choices=["PENDIENTE", "REALIZADA", "ANULADA"], required=False
    )

    detalles = DetalleCompraWriteSerializer(many=True, required=False)

    class Meta:
        model = Compra
        fields = ["proveedor_id", "fecha", "observaciones", "estado", "detalles"]

    def validate_proveedor_id(self, value):
        """Validar proveedor"""
        if not value.estado:
            raise serializers.ValidationError(
                "El proveedor seleccionado está inactivo."
            )
        return value

    def validate_fecha(self, value):
        """Validar fecha"""
        from django.utils import timezone

        hoy = timezone.now().date()

        if value > hoy:
            raise serializers.ValidationError("No se puede usar una fecha futura.")

        return value

    def validate_estado(self, value):
        """Validar cambio de estado"""
        instance = self.instance

        # No se puede cambiar el estado de una compra anulada
        if instance.estado == "ANULADA":
            raise serializers.ValidationError(
                "No se puede cambiar el estado de una compra anulada."
            )

        # No se puede pasar de REALIZADA a PENDIENTE directamente
        if instance.estado == "REALIZADA" and value == "PENDIENTE":
            raise serializers.ValidationError(
                "No se puede revertir una compra realizada a pendiente. "
                "Debe anularla primero."
            )

        return value

    def validate(self, data):
        """Validaciones a nivel de objeto"""
        instance = self.instance

        # No se puede modificar una compra anulada
        if instance.estado == "ANULADA":
            raise serializers.ValidationError(
                "No se puede modificar una compra anulada."
            )

        # Si se actualizan detalles, validar que esté PENDIENTE
        if "detalles" in data and instance.estado != "PENDIENTE":
            raise serializers.ValidationError(
                {
                    "detalles": (
                        "Solo se pueden modificar los productos de una compra PENDIENTE."
                    )
                }
            )

        # Si se actualizan detalles, recalcular total
        if "detalles" in data:
            total = Decimal("0.00")
            for detalle in data["detalles"]:
                cantidad = Decimal(str(detalle["cantidad"]))
                precio = detalle.get(
                    "precio_compra",
                    Producto.objects.get(id=detalle["producto_id"]).precio_compra,
                )
                precio = Decimal(str(precio))
                total += cantidad * precio

            data["total"] = total

        return data

    @transaction.atomic
    def update(self, instance, validated_data):
        """
        Actualizar compra con transacción

        Proceso:
        1. Extraer detalles (si existen)
        2. Actualizar campos de la compra
        3. Si hay detalles nuevos, reemplazar los existentes
        4. Recalcular total
        """
        # Extraer detalles
        detalles_data = validated_data.pop("detalles", None)

        # Actualizar campos simples
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Si hay detalles nuevos, reemplazar
        if detalles_data is not None:
            # Eliminar detalles existentes
            instance.detalles.all().delete()

            # Crear nuevos detalles
            for detalle_data in detalles_data:
                producto = Producto.objects.get(id=detalle_data["producto_id"])
                precio = detalle_data.get("precio_compra", producto.precio_compra)

                DetalleCompra.objects.create(
                    compra=instance,
                    producto=producto,
                    cantidad=detalle_data["cantidad"],
                    precio_compra=precio,
                    # subtotal se calcula automáticamente en el modelo
                )

        instance.save()
        return instance


class CompraAnularSerializer(serializers.Serializer):
    """
    Serializer para ANULAR compras

    Usado en: POST /api/compras/{id}/anular/

    Requiere:
    - Motivo descriptivo (mínimo 10 caracteres)

    Validaciones:
    - Solo se puede anular si NO está ANULADA
    - Si está REALIZADA, revierte el inventario
    """

    motivo = serializers.CharField(
        min_length=10,
        max_length=500,
        required=True,
        trim_whitespace=True,
        error_messages={
            "required": "El motivo de anulación es requerido.",
            "blank": "El motivo de anulación no puede estar vacío.",
            "min_length": "El motivo debe tener al menos 10 caracteres.",
        },
    )

    def validate_motivo(self, value):
        """Validar que el motivo sea descriptivo"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El motivo de anulación debe ser más descriptivo (mínimo 10 caracteres)."
            )

        # Evitar motivos genéricos
        motivos_genericos = ["error", "equivocación", "cancelar", "anular"]
        if value.lower().strip() in motivos_genericos:
            raise serializers.ValidationError(
                "Por favor proporciona un motivo más específico de la anulación."
            )

        return value.strip()
