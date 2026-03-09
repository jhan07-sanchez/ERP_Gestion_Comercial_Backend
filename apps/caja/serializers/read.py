# apps/caja/serializers/read.py
"""
Serializers de LECTURA para el módulo Caja (GET requests)

📚 ¿Por qué separar read y write?

READ (lectura): Devuelve muchos campos, incluye datos de relaciones,
campos calculados, etc. Son ricos en información para el frontend.

WRITE (escritura): Solo acepta los campos necesarios para crear/editar.
Son más estrictos y con validaciones.

Separar ambos evita problemas como:
- No puedes poner campos read_only y write_only en el mismo serializer
- La validación de escritura no contamina la representación de lectura
"""

from rest_framework import serializers
from apps.caja.models import MetodoPago, Caja, SesionCaja, MovimientoCaja, ArqueoCaja


# ============================================================================
# MÉTODO DE PAGO
# ============================================================================


class MetodoPagoSerializer(serializers.ModelSerializer):
    """Serializer para listar/ver métodos de pago"""

    class Meta:
        model = MetodoPago
        fields = ["id", "nombre", "activo", "es_efectivo", "fecha_creacion"]


class MetodoPagoSimpleSerializer(serializers.ModelSerializer):
    """Versión compacta para usar en relaciones"""

    class Meta:
        model = MetodoPago
        fields = ["id", "nombre", "es_efectivo"]


# ============================================================================
# CAJA
# ============================================================================


class CajaListSerializer(serializers.ModelSerializer):
    """Para listar cajas - vista resumida"""

    esta_abierta = serializers.BooleanField(read_only=True)
    usuario_activo = serializers.SerializerMethodField()

    class Meta:
        model = Caja
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activa",
            "esta_abierta",
            "usuario_activo",
            "fecha_creacion",
        ]

    def get_usuario_activo(self, obj):
        """Si hay sesión abierta, retornar el username del usuario"""
        sesion = obj.sesion_activa
        if sesion:
            return sesion.usuario.username
        return None


class CajaDetailSerializer(serializers.ModelSerializer):
    """Para ver detalle de una caja"""

    esta_abierta = serializers.BooleanField(read_only=True)
    sesion_activa_id = serializers.SerializerMethodField()
    total_sesiones = serializers.SerializerMethodField()

    class Meta:
        model = Caja
        fields = [
            "id",
            "nombre",
            "descripcion",
            "activa",
            "esta_abierta",
            "sesion_activa_id",
            "total_sesiones",
            "fecha_creacion",
            "fecha_actualizacion",
        ]

    def get_sesion_activa_id(self, obj):
        sesion = obj.sesion_activa
        return sesion.id if sesion else None

    def get_total_sesiones(self, obj):
        return obj.sesiones.count()


# ============================================================================
# MOVIMIENTO DE CAJA
# ============================================================================


class MovimientoCajaListSerializer(serializers.ModelSerializer):
    """Para listar movimientos - vista resumida"""

    metodo_pago_nombre = serializers.CharField(
        source="metodo_pago.nombre", read_only=True
    )
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    es_ingreso = serializers.BooleanField(read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = MovimientoCaja
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "es_ingreso",
            "monto",
            "descripcion",
            "metodo_pago",
            "metodo_pago_nombre",
            "usuario_nombre",
            "fecha",
        ]


class MovimientoCajaDetailSerializer(serializers.ModelSerializer):
    """Para ver detalle de un movimiento"""

    metodo_pago_info = MetodoPagoSimpleSerializer(source="metodo_pago", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    es_ingreso = serializers.BooleanField(read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    venta_id = serializers.IntegerField(
        source="referencia_venta.id", read_only=True, default=None
    )
    compra_id = serializers.IntegerField(
        source="referencia_compra.id", read_only=True, default=None
    )

    class Meta:
        model = MovimientoCaja
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "es_ingreso",
            "monto",
            "descripcion",
            "metodo_pago",
            "metodo_pago_info",
            "usuario",
            "usuario_nombre",
            "venta_id",
            "compra_id",
            "fecha",
        ]


# ============================================================================
# ARQUEO DE CAJA
# ============================================================================


class ArqueoCajaSerializer(serializers.ModelSerializer):
    """Para ver arqueos"""

    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    tiene_diferencia = serializers.SerializerMethodField()

    class Meta:
        model = ArqueoCaja
        fields = [
            "id",
            "tipo",
            "tipo_display",
            "monto_contado",
            "monto_esperado",
            "diferencia",
            "tiene_diferencia",
            "detalle_billetes",
            "observaciones",
            "usuario",
            "usuario_nombre",
            "fecha",
        ]

    def get_tiene_diferencia(self, obj):
        """¿Hay diferencia entre contado y esperado?"""
        return obj.diferencia != 0


# ============================================================================
# SESIÓN DE CAJA
# ============================================================================


class SesionCajaListSerializer(serializers.ModelSerializer):
    """Para listar sesiones - vista resumida"""

    caja_nombre = serializers.CharField(source="caja.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    total_movimientos = serializers.SerializerMethodField()
    saldo_esperado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = SesionCaja
        fields = [
            "id",
            "caja",
            "caja_nombre",
            "usuario",
            "usuario_nombre",
            "estado",
            "estado_display",
            "monto_inicial",
            "monto_final",
            "monto_contado",
            "saldo_esperado",
            "fecha_apertura",
            "fecha_cierre",
            "total_movimientos",
        ]

    def get_total_movimientos(self, obj):
        return obj.movimientos.count()


class SesionCajaDetailSerializer(serializers.ModelSerializer):
    """Para ver detalle completo de una sesión"""

    caja_nombre = serializers.CharField(source="caja.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    # Propiedades calculadas
    total_ingresos = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    total_egresos = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    saldo_esperado = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )
    diferencia = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True, allow_null=True
    )

    # Movimientos y arqueos incluidos
    movimientos = MovimientoCajaListSerializer(many=True, read_only=True)
    arqueos = ArqueoCajaSerializer(many=True, read_only=True)

    class Meta:
        model = SesionCaja
        fields = [
            "id",
            "caja",
            "caja_nombre",
            "usuario",
            "usuario_nombre",
            "estado",
            "estado_display",
            "monto_inicial",
            "monto_final",
            "monto_contado",
            "total_ingresos",
            "total_egresos",
            "saldo_esperado",
            "diferencia",
            "fecha_apertura",
            "fecha_cierre",
            "observaciones_apertura",
            "observaciones_cierre",
            "movimientos",
            "arqueos",
        ]
