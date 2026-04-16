from rest_framework import serializers
from apps.documentos.models import Documento, DocumentoDetalle

class DocumentoDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoDetalle
        fields = ['id', 'orden', 'descripcion', 'producto_id', 'cantidad', 'precio_unitario', 'subtotal']

class DocumentoListSerializer(serializers.ModelSerializer):
    entidad_nombre = serializers.SerializerMethodField()
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)

    class Meta:
        model = Documento
        fields = [
            'id', 'uuid', 'tipo', 'tipo_display', 'estado', 'estado_display',
            'numero_interno', 'codigo_verificacion', 'entidad_nombre', 'total',
            'fecha_emision', 'usuario_nombre',
        ]

    def get_entidad_nombre(self, obj) -> str:
        if obj.venta and obj.venta.cliente: return obj.venta.cliente.nombre
        if obj.compra and obj.compra.proveedor: return obj.compra.proveedor.nombre
        return "N/A"

class DocumentoDetailSerializer(serializers.ModelSerializer):
    lineas = DocumentoDetalleSerializer(many=True, read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.username', read_only=True)
    referencia_detallada = serializers.SerializerMethodField()

    class Meta:
        model = Documento
        fields = [
            'id', 'uuid', 'tipo', 'tipo_display', 'estado', 'estado_display',
            'numero_interno', 'numero_secuencia', 'codigo_verificacion', 'hash_verificacion',
            'subtotal', 'impuestos', 'total', 'fecha_emision', 'fecha_vencimiento',
            'referencia_operacion', 'referencia_detallada', 'usuario_nombre', 'notas', 'lineas',
        ]

    def get_referencia_detallada(self, obj) -> dict:
        res = {"venta_id": obj.venta_id, "compra_id": obj.compra_id}
        if obj.venta: res["numero"] = obj.venta.numero_documento
        elif obj.compra: res["numero"] = obj.compra.numero_compra
        return res
