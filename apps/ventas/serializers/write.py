# apps/ventas/serializers/write.py
"""
Serializers de ESCRITURA para Ventas

Este archivo contiene los serializers para:
- Crear datos de ventas (POST requests)
- Actualizar datos (PUT/PATCH requests)
- Validaciones específicas de escritura

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from django.db import transaction
from apps.ventas.models import Venta, DetalleVenta, PagoVenta
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.inventario.models import Inventario


# ============================================================================
# SERIALIZERS DE DETALLE DE VENTA (WRITE)
# ============================================================================

class DetalleVentaWriteSerializer(serializers.Serializer):
    """
    Serializer de escritura para Detalle de Venta
    
    Usado en:
    - Crear detalles de venta
    
    Nota: Es un Serializer (no ModelSerializer) porque
    hacemos validaciones personalizadas complejas
    """
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)
    precio_unitario = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False  # Se toma del producto si no se proporciona
    )
    
    def validate_producto_id(self, value):
        """Validar que el producto existe y está activo"""
        try:
            producto = Producto.objects.get(id=value)
            if not producto.estado:
                raise serializers.ValidationError(
                    f"El producto '{producto.nombre}' está inactivo."
                )
            return value
        except Producto.DoesNotExist:
            raise serializers.ValidationError(
                f"El producto con ID {value} no existe."
            )
    
    def validate_cantidad(self, value):
        """Validar cantidad positiva"""
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a 0."
            )
        if value > 10000:
            raise serializers.ValidationError(
                "La cantidad es demasiado grande. Verifica el valor."
            )
        return value
    
    def validate(self, data):
        """
        Validaciones a nivel de objeto
        
        Valida:
        1. Que haya stock suficiente
        2. Que el precio sea válido
        """
        producto_id = data.get('producto_id')
        cantidad = data.get('cantidad')
        
        # Validar stock suficiente
        try:
            producto = Producto.objects.get(id=producto_id)
            inventario = Inventario.objects.get(producto=producto)
            
            if inventario.stock_actual < cantidad:
                raise serializers.ValidationError({
                    'cantidad': (
                        f'Stock insuficiente. '
                        f'Disponible: {inventario.stock_actual}, '
                        f'Solicitado: {cantidad}'
                    )
                })
        except Inventario.DoesNotExist:
            raise serializers.ValidationError({
                'producto_id': f'El producto no tiene inventario registrado.'
            })
        
        # Si no se proporciona precio, usar el del producto
        if 'precio_unitario' not in data or data['precio_unitario'] is None:
            data['precio_unitario'] = producto.precio_venta
        
        # Validar que el precio sea razonable
        if data['precio_unitario'] <= 0:
            raise serializers.ValidationError({
                'precio_unitario': 'El precio debe ser mayor a 0.'
            })
        
        return data


# ============================================================================
# SERIALIZERS DE PAGO DE VENTA (WRITE)
# ============================================================================

class PagoVentaCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para REGISTRAR un nuevo pago a una venta.
    Validaremos en el servicio que el monto no exceda el saldo pendiente.
    """
    class Meta:
        model = PagoVenta
        fields = [
            'monto', 
            'metodo_pago', 
            'monto_recibido', 
            'vuelto', 
            'referencia'
        ]
        
    def validate_monto(self, value):
        if value <= 0:
            raise serializers.ValidationError("El monto del pago debe ser mayor a 0.")
        return value

# ============================================================================
# SERIALIZERS DE VENTA (WRITE)
# ============================================================================

class VentaCreateSerializer(serializers.Serializer):
    """
    Serializer para CREAR ventas
    
    Usado en:
    - POST /api/ventas/
    
    Al crear una venta:
    1. Valida cliente y productos
    2. Verifica stock
    3. Crea venta y detalles
    4. Reduce stock automáticamente
    """
    cliente_id = serializers.IntegerField()
    detalles = DetalleVentaWriteSerializer(many=True)
    estado = serializers.ChoiceField(
        choices=['PENDIENTE', 'PARCIAL', 'COMPLETADA'],
        default='PENDIENTE',
        required=False
    )
    tipo_documento = serializers.ChoiceField(
        choices=['FACTURA', 'RECIBO'],
        default='FACTURA',
        required=False
    )
    
    def validate_cliente_id(self, value):
        """Validar que el cliente existe y está activo"""
        try:
            cliente = Cliente.objects.get(id=value)
            if not cliente.estado:
                raise serializers.ValidationError(
                    f"El cliente '{cliente.nombre}' está inactivo."
                )
            return value
        except Cliente.DoesNotExist:
            raise serializers.ValidationError(
                f"El cliente con ID {value} no existe."
            )
    
    def validate_detalles(self, value):
        """Validar que haya al menos un detalle"""
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Debe incluir al menos un producto en la venta."
            )
        
        if len(value) > 100:
            raise serializers.ValidationError(
                "No puede incluir más de 100 productos en una venta."
            )
        
        # Validar que no haya productos duplicados
        productos_ids = [detalle['producto_id'] for detalle in value]
        if len(productos_ids) != len(set(productos_ids)):
            raise serializers.ValidationError(
                "No puede incluir el mismo producto múltiples veces. "
                "Use la cantidad para indicar más unidades."
            )
        
        return value
    
    def validate(self, data):
        """
        Validaciones a nivel de venta
        
        Calcula el total de la venta
        """
        detalles = data.get('detalles', [])
        
        # Calcular total
        total = sum(
            detalle['cantidad'] * detalle.get(
                'precio_unitario',
                Producto.objects.get(id=detalle['producto_id']).precio_venta
            )
            for detalle in detalles
        )
        
        
        data['total'] = total
        
        return data


class VentaUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR ventas
    
    Usado en:
    - PUT/PATCH /api/ventas/{id}/
    
    Permite actualizar:
    - Cliente
    - Detalles (productos, cantidades, precios)
    - Estado
    """
    cliente_id = serializers.IntegerField(required=False)
    detalles = DetalleVentaWriteSerializer(many=True, required=False)
    
    class Meta:
        model = Venta
        fields = ['cliente_id', 'detalles', 'estado']
    
    def update(self, instance, validated_data):
        """
        Sobrescribir update para usar el servicio y manejar detalles anidados
        """
        from apps.ventas.services import VentaService
        
        # Si se proporcionan detalles o cliente, usar el servicio para la actualización completa
        if 'detalles' in validated_data or 'cliente_id' in validated_data:
            cliente_id = validated_data.get('cliente_id', instance.cliente.id)
            detalles = validated_data.get('detalles', [])
            
            # Si no se pasaron detalles, pero sí cliente u otro campo, 
            # y el serializer se usa en PATCH parcial, debemos decidir qué hacer.
            # En este caso, si llega la llave 'detalles' vacía o presente, actualizamos.
            
            venta = VentaService.actualizar_venta(
                venta_id=instance.id,
                cliente_id=cliente_id,
                detalles=detalles,
                usuario=self.context['request'].user
            )
            
            # El estado se puede actualizar también
            if 'estado' in validated_data:
                venta.estado = validated_data['estado']
                venta.save()
                
            return venta
            
        # Si solo se actualiza el estado (comportamiento original)
        return super().update(instance, validated_data)
    
    def validate_estado(self, value):
        """
        Validar cambios de estado
        
        Reglas:
        - PENDIENTE → COMPLETADA: OK
        - PENDIENTE → CANCELADA: OK
        - COMPLETADA → CANCELADA: NO (requiere permiso especial)
        - CANCELADA → cualquier otro: NO
        """
        instance = self.instance
        
        if instance.estado == 'CANCELADA':
            raise serializers.ValidationError(
                "No se puede modificar una venta cancelada."
            )
        
        if instance.estado == 'COMPLETADA' and value == 'CANCELADA':
            raise serializers.ValidationError(
                "No se puede cancelar una venta completada desde aquí. "
                "Use el endpoint de cancelación especial."
            )
        
        return value


class VentaCancelarSerializer(serializers.Serializer):
    """
    Serializer para CANCELAR ventas
    
    Usado en:
    - POST /api/ventas/{id}/cancelar/
    
    Requiere motivo de cancelación
    """
    motivo = serializers.CharField(
        min_length=10,
        max_length=500,
        required=True
    )
    
    def validate_motivo(self, value):
        """El motivo debe ser descriptivo"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El motivo de cancelación debe tener al menos 10 caracteres."
            )
        return value.strip()


class VentaCompletarSerializer(serializers.Serializer):
    """
    Serializer para COMPLETAR ventas pendientes
    
    Usado en:
    - POST /api/ventas/{id}/completar/
    """
    notas = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True
    )