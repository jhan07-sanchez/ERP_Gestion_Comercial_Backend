from rest_framework import serializers
from apps.facturacion.models import PagoFactura

class PagoFacturaSerializer(serializers.ModelSerializer):
    metodo_pago_nombre = serializers.ReadOnlyField(source='metodo_pago.nombre')
    registrado_por_nombre = serializers.ReadOnlyField(source='registrado_por.username')

    class Meta:
        model = PagoFactura
        fields = [
            'id', 'factura', 'metodo_pago', 'metodo_pago_nombre', 
            'monto', 'referencia', 'observaciones', 
            'fecha', 'registrado_por', 'registrado_por_nombre'
        ]
        read_only_fields = ['id', 'factura', 'fecha', 'registrado_por']

class RegistrarPagoSerializer(serializers.Serializer):
    metodo_pago_id = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=14, decimal_places=2)
    referencia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
