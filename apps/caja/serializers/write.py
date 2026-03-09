# apps/caja/serializers/write.py
"""
Serializers de ESCRITURA para el módulo Caja (POST, PUT, PATCH)

📚 Los write serializers tienen:
- Validaciones de campo
- Validaciones cruzadas (entre campos)
- Solo los campos que el usuario puede enviar
"""

from rest_framework import serializers
from decimal import Decimal
from apps.caja.models import MetodoPago, Caja, SesionCaja, MovimientoCaja, ArqueoCaja


# ============================================================================
# MÉTODO DE PAGO
# ============================================================================


class MetodoPagoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = ["nombre", "es_efectivo"]

    def validate_nombre(self, value):
        """El nombre no puede estar vacío ni ser duplicado"""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("El nombre no puede estar vacío")
        if MetodoPago.objects.filter(nombre__iexact=value).exists():
            raise serializers.ValidationError(
                f'Ya existe un método de pago con el nombre "{value}"'
            )
        return value


# ============================================================================
# CAJA
# ============================================================================


class CajaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caja
        fields = ["nombre", "descripcion"]

    def validate_nombre(self, value):
        value = value.strip()
        if Caja.objects.filter(nombre__iexact=value).exists():
            raise serializers.ValidationError(
                f'Ya existe una caja con el nombre "{value}"'
            )
        return value


class CajaUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Caja
        fields = ["nombre", "descripcion", "activa"]


# ============================================================================
# SESIÓN DE CAJA — APERTURA
# ============================================================================


class AbrirCajaSerializer(serializers.Serializer):
    """
    Datos para abrir una caja.

    📚 Usamos Serializer (no ModelSerializer) porque no todos los campos
    vienen directamente del modelo. El campo 'usuario' lo tomamos del
    request, no del body.
    """

    caja_id = serializers.IntegerField(help_text="ID de la caja a abrir")
    monto_inicial = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text="Dinero con el que se abre la caja (puede ser 0)",
    )
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Notas opcionales de apertura",
    )

    def validate_caja_id(self, value):
        from apps.caja.models import Caja

        if not Caja.objects.filter(id=value, activa=True).exists():
            raise serializers.ValidationError(
                f"No existe una caja activa con ID {value}"
            )
        return value


# ============================================================================
# SESIÓN DE CAJA — CIERRE
# ============================================================================


class CerrarCajaSerializer(serializers.Serializer):
    """Datos para cerrar una caja"""

    monto_contado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text="Total del dinero contado físicamente",
    )
    detalle_billetes = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        required=False,
        default=dict,
        help_text='Ej: {"100000": 3, "50000": 2} → 3 billetes de $100k, 2 de $50k',
    )
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
    )


# ============================================================================
# MOVIMIENTO DE CAJA
# ============================================================================


class MovimientoCajaCreateSerializer(serializers.Serializer):
    """
    Datos para registrar un movimiento manual.

    No incluye APERTURA (se hace automático) ni INGRESO_VENTA / EGRESO_COMPRA
    (esos los generan los módulos de ventas y compras automáticamente).

    Los tipos manuales son:
    - INGRESO_MANUAL
    - EGRESO_GASTO
    - EGRESO_RETIRO
    """

    TIPOS_MANUALES = [
        MovimientoCaja.INGRESO_MANUAL,
        MovimientoCaja.EGRESO_GASTO,
        MovimientoCaja.EGRESO_RETIRO,
    ]

    tipo = serializers.ChoiceField(
        choices=[
            (MovimientoCaja.INGRESO_MANUAL, "Ingreso manual"),
            (MovimientoCaja.EGRESO_GASTO, "Egreso por gasto"),
            (MovimientoCaja.EGRESO_RETIRO, "Retiro de dinero"),
        ],
        help_text="Tipo de movimiento",
    )
    monto = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        help_text="Valor del movimiento (mayor a cero)",
    )
    descripcion = serializers.CharField(
        max_length=500, help_text="Descripción del movimiento"
    )
    metodo_pago_id = serializers.IntegerField(help_text="ID del método de pago")

    def validate_descripcion(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("La descripción no puede estar vacía")
        return value

    def validate_metodo_pago_id(self, value):
        from apps.caja.models import MetodoPago

        if not MetodoPago.objects.filter(id=value, activo=True).exists():
            raise serializers.ValidationError(
                f"No existe método de pago activo con ID {value}"
            )
        return value


# ============================================================================
# ARQUEO DE CAJA
# ============================================================================


class ArqueoCajaSerializer(serializers.Serializer):
    """Datos para realizar un arqueo"""

    monto_contado = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text="Total del dinero contado físicamente",
    )
    detalle_billetes = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        required=False,
        default=dict,
        help_text='Ej: {"100000": 3, "50000": 5}',
    )
    observaciones = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Notas sobre la diferencia encontrada",
    )
