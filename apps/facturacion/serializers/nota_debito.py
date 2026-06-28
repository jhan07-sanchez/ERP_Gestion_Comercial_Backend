from rest_framework import serializers
from apps.facturacion.models import NotaDebito, NotaDebitoDetalle


class NotaDebitoDetalleSerializer(serializers.ModelSerializer):
    """Serializer de lectura para detalles de Nota de Débito."""
    class Meta:
        model = NotaDebitoDetalle
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_codigo',
            'cantidad', 'precio_unitario', 'subtotal'
        ]
        read_only_fields = ['id', 'subtotal']


class NotaDebitoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados de Notas de Débito."""
    factura_numero = serializers.ReadOnlyField(source='factura.numero')
    creado_por_nombre = serializers.ReadOnlyField(source='creado_por.username')

    class Meta:
        model = NotaDebito
        fields = [
            'id', 'numero', 'factura', 'factura_numero',
            'motivo', 'total', 'estado', 'fecha_emision',
            'creado_por', 'creado_por_nombre'
        ]


class NotaDebitoDetailSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle de una Nota de Débito."""
    detalles = NotaDebitoDetalleSerializer(many=True, read_only=True)
    factura_numero = serializers.ReadOnlyField(source='factura.numero')
    creado_por_nombre = serializers.ReadOnlyField(source='creado_por.username')

    class Meta:
        model = NotaDebito
        fields = [
            'id', 'numero', 'factura', 'factura_numero',
            'motivo', 'subtotal', 'impuesto', 'total',
            'estado', 'fecha_emision',
            'creado_por', 'creado_por_nombre',
            'detalles'
        ]


class NotaDebitoDetalleCreateSerializer(serializers.Serializer):
    """Serializer de escritura para cada línea de detalle."""
    producto_id = serializers.IntegerField(required=False, allow_null=True)
    producto_nombre = serializers.CharField(max_length=255, required=False, default='Concepto')
    producto_codigo = serializers.CharField(max_length=100, required=False, default='N/A')
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)
    precio_unitario = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class NotaDebitoCreateSerializer(serializers.Serializer):
    """Serializer para crear una Nota de Débito en BORRADOR."""
    factura_id = serializers.IntegerField()
    motivo = serializers.CharField(max_length=500)
    detalles = NotaDebitoDetalleCreateSerializer(many=True)

    def validate_detalles(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos una línea de detalle.")
        return value


class AnularNotaDebitoSerializer(serializers.Serializer):
    """Serializer para la acción de anular una Nota de Débito."""
    motivo = serializers.CharField(max_length=255)
