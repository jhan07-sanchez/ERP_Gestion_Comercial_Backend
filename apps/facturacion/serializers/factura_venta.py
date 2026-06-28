from rest_framework import serializers
from apps.facturacion.models import Factura, FacturaDetalle, FacturaImpuesto
from apps.facturacion.serializers.pago import PagoFacturaSerializer

class FacturaDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    producto_codigo = serializers.ReadOnlyField(source='producto.codigo')
    stock_disponible = serializers.SerializerMethodField()

    class Meta:
        model = FacturaDetalle
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_codigo', 
            'cantidad', 'precio_unitario', 'descuento', 
            'subtotal', 'impuestos_linea', 'total_linea', 'stock_disponible'
        ]
        read_only_fields = ['subtotal', 'total_linea']

    def get_stock_disponible(self, obj):
        try:
            return obj.producto.inventario.stock_actual
        except Exception:
            return 0

class FacturaImpuestoSerializer(serializers.ModelSerializer):
    impuesto_nombre = serializers.ReadOnlyField(source='impuesto.nombre')

    class Meta:
        model = FacturaImpuesto
        fields = ['id', 'impuesto', 'impuesto_nombre', 'base_imponible', 'monto']

class FacturaListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre')
    cliente_documento = serializers.ReadOnlyField(source='cliente.numero_documento')

    class Meta:
        model = Factura
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre', 'cliente_documento',
            'estado', 'fecha_emision', 'fecha_vencimiento', 
            'total', 'saldo_pendiente'
        ]

class FacturaDetailSerializer(serializers.ModelSerializer):
    detalles = FacturaDetalleSerializer(many=True, read_only=True)
    desglose_impuestos = FacturaImpuestoSerializer(many=True, read_only=True)
    pagos = PagoFacturaSerializer(many=True, read_only=True)
    cliente_nombre = serializers.ReadOnlyField(source='cliente.nombre')
    cliente_documento = serializers.ReadOnlyField(source='cliente.numero_documento')
    vendedor_nombre = serializers.ReadOnlyField(source='vendedor.get_full_name', default=None)
    creado_por_nombre = serializers.ReadOnlyField(source='creado_por.username')

    class Meta:
        model = Factura
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre', 'cliente_documento',
            'estado', 'documento', 'fecha_emision', 'fecha_vencimiento',
            'subtotal', 'descuento_total', 'impuestos_total', 'total', 'saldo_pendiente',
            'observaciones', 'vendedor', 'vendedor_nombre', 'creado_por', 'creado_por_nombre',
            'fecha_creacion', 'fecha_actualizacion', 'detalles', 'desglose_impuestos', 'pagos'
        ]

class FacturaDetalleCreateSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = serializers.DecimalField(max_digits=14, decimal_places=2)
    descuento = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)
    impuestos_linea = serializers.DecimalField(max_digits=14, decimal_places=2, required=False, default=0)

class FacturaCreateSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField()
    vendedor_id = serializers.IntegerField(required=False, allow_null=True)
    detalles = FacturaDetalleCreateSerializer(many=True)
    fecha_emision = serializers.DateField(required=False, allow_null=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

class FacturaUpdateSerializer(serializers.Serializer):
    """
    Solo permitimos actualizar el cliente y detalles si está en BORRADOR.
    """
    cliente_id = serializers.IntegerField(required=False)
    detalles = FacturaDetalleCreateSerializer(many=True, required=False)
    fecha_emision = serializers.DateField(required=False, allow_null=True)
    fecha_vencimiento = serializers.DateField(required=False, allow_null=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)

class AnularFacturaSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=255)
