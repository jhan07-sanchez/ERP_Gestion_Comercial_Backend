# apps/compras/serializers/write.py
"""
Serializers de ESCRITURA para Compras

Este archivo contiene los serializers para:
- Crear datos de compras (POST requests)
- Actualizar datos (PUT/PATCH requests)
- Validaciones específicas de escritura

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from django.db import transaction
from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto
from apps.proveedores.models import Proveedor


# ============================================================================
# SERIALIZERS DE DETALLE DE COMPRA (WRITE)
# ============================================================================

class DetalleCompraWriteSerializer(serializers.Serializer):
    """
    Serializer de escritura para Detalle de Compra
    
    Usado en:
    - Crear detalles de compra
    
    Nota: Es un Serializer (no ModelSerializer) porque
    hacemos validaciones personalizadas complejas
    """
    producto_id = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)
    precio_compra = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False  # Se toma del producto si no se proporciona
    )
    
    def validate_producto_id(self, value):
        """Validar que el producto existe"""
        try:
            producto = Producto.objects.get(id=value)
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
        if value > 100000:
            raise serializers.ValidationError(
                "La cantidad es demasiado grande. Verifica el valor."
            )
        return value
    
    def validate(self, data):
        """
        Validaciones a nivel de objeto
        
        Valida:
        1. Que el precio sea válido
        """
        producto_id = data.get('producto_id')
        
        # Si no se proporciona precio, usar el del producto
        if 'precio_compra' not in data or data['precio_compra'] is None:
            producto = Producto.objects.get(id=producto_id)
            data['precio_compra'] = producto.precio_compra
        
        # Validar que el precio sea positivo
        if data['precio_compra'] <= 0:
            raise serializers.ValidationError({
                'precio_compra': 'El precio debe ser mayor a 0.'
            })
        
        return data


# ============================================================================
# SERIALIZERS DE COMPRA (WRITE)
# ============================================================================

class CompraCreateSerializer(serializers.Serializer):
    """
    Serializer para CREAR compras
    
    Usado en:
    - POST /api/compras/
    
    Al crear una compra:
    1. Valida proveedor y productos
    2. Crea compra y detalles
    3. Aumenta stock automáticamente
    """
    proveedor = serializers.IntegerField()
    detalles = DetalleCompraWriteSerializer(many=True)
    
    def validate_proveedor(self, value):
        """Validar que el proveedor exista"""
        try:
            proveedor = Proveedor.objects.get(id=value)
            return value
        except Proveedor.DoesNotExist:
            raise serializers.ValidationError(
                f"El proveedor con ID {value} no existe."
            )
    
    def validate_detalles(self, value):
        """Validar que haya al menos un detalle"""
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Debe incluir al menos un producto en la compra."
            )
        
        if len(value) > 100:
            raise serializers.ValidationError(
                "El nombre del proveedor es requerido."
            )
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre del proveedor debe tener al menos 3 caracteres."
            )
        return value.strip()
    
    def validate_detalles(self, value):
        """Validar que haya al menos un detalle"""
        if not value or len(value) == 0:
            raise serializers.ValidationError(
                "Debe incluir al menos un producto en la compra."
            )
        
        if len(value) > 100:
            raise serializers.ValidationError(
                "No puede incluir más de 100 productos en una compra."
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
        Validaciones a nivel de compra
        
        Calcula el total de la compra
        """
        detalles = data.get('detalles', [])
        
        # Calcular total
        total = sum(
            detalle['cantidad'] * detalle.get(
                'precio_compra',
                Producto.objects.get(id=detalle['producto_id']).precio_compra
            )
            for detalle in detalles
        )
        
        data['total'] = total
        
        return data


class CompraUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR compras
    
    Usado en:
    - PUT/PATCH /api/compras/{id}/
    
    Nota: Solo se puede actualizar el proveedor.
    Los detalles NO se pueden modificar una vez creados.
    """
    
    class Meta:
        model = Compra
        fields = ['proveedor']
    
    def validate_proveedor(self, value):
        """Validar el nombre del proveedor"""
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError(
                "El nombre del proveedor es requerido."
            )
        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre del proveedor debe tener al menos 3 caracteres."
            )
        return value.strip()


class CompraAnularSerializer(serializers.Serializer):
    """
    Serializer para ANULAR compras
    
    Usado en:
    - POST /api/compras/{id}/anular/
    
    Requiere motivo de anulación
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
                "El motivo de anulación debe tener al menos 10 caracteres."
            )
        return value.strip()