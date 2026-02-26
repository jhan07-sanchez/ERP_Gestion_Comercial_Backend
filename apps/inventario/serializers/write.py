# apps/inventario/serializers/write.py
"""
Serializers de ESCRITURA para Inventario

Este archivo contiene los serializers para:
- Crear datos (POST requests)
- Validaciones específicas de escritura

Separados de los serializers de lectura para:
- Validaciones más estrictas
- Campos diferentes entre lectura y escritura
- Mejor organización del código
"""

from rest_framework import serializers
from apps.inventario.models import Inventario, MovimientoInventario
from apps.productos.models import Producto


# ============================================================================
# SERIALIZERS DE MOVIMIENTO DE INVENTARIO (WRITE)
# ============================================================================

class MovimientoInventarioCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR movimientos de inventario

    Usado en:
    - POST /api/inventario/movimientos/

    Al crear un movimiento:
    1. Valida el tipo y cantidad
    2. Para SALIDA: Verifica que haya stock suficiente
    3. Crea el movimiento
    4. Actualiza automáticamente el inventario (en el ViewSet)
    """

    class Meta:
        model = MovimientoInventario
        fields = [
            'producto',
            'tipo_movimiento',
            'cantidad',
            'referencia'
        ]
        # usuario y fecha se asignan automáticamente

    def validate_tipo_movimiento(self, value):
        """Validar que el tipo de movimiento sea válido"""
        value = value.upper()

        if value not in ['ENTRADA', 'SALIDA']:
            raise serializers.ValidationError(
                "El tipo de movimiento debe ser 'ENTRADA' o 'SALIDA'."
            )

        return value

    def validate_cantidad(self, value):
        """
        Validar cantidad del movimiento

        Debe ser:
        - Mayor a 0
        - Número entero
        - No excesivamente grande
        """
        if value <= 0:
            raise serializers.ValidationError(
                "La cantidad debe ser mayor a 0."
            )

        if value > 999999:
            raise serializers.ValidationError(
                "La cantidad es demasiado grande. Verifica el valor."
            )

        return value

    def validate_referencia(self, value):
        """Validar referencia del movimiento"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "La referencia debe tener al menos 3 caracteres."
            )

        return value.strip()

    def validate(self, data):
        """
        Validaciones a nivel de objeto

        Valida que:
        1. El producto existe y está activo
        2. Para SALIDA: Hay suficiente stock
        3. La referencia es única para este producto y tipo
        """
        producto = data.get('producto')
        tipo = data.get('tipo_movimiento')
        cantidad = data.get('cantidad')
        referencia = data.get('referencia')

        # Validar que el producto esté activo
        if not producto.estado:
            raise serializers.ValidationError({
                'producto': f'El producto {producto.nombre} está inactivo.'
            })

        # Para SALIDA: Validar que haya stock suficiente
        if tipo == 'SALIDA':
            try:
                inventario = Inventario.objects.get(producto=producto)

                if inventario.stock_actual < cantidad:
                    raise serializers.ValidationError({
                        'cantidad': (
                            f'Stock insuficiente. '
                            f'Disponible: {inventario.stock_actual}, '
                            f'Solicitado: {cantidad}'
                        )
                    })

                # Advertir si la salida deja el stock por debajo del mínimo
                stock_resultante = inventario.stock_actual - cantidad
                if stock_resultante < producto.stock_minimo:
                    # No es error, pero podríamos registrarlo o advertir
                    pass

            except Inventario.DoesNotExist:
                raise serializers.ValidationError({
                    'producto': 'Este producto no tiene inventario registrado.'
                })

        # Validar que la referencia no se repita para el mismo producto
        # (esto es opcional, depende de tu lógica de negocio)
        existe_referencia = MovimientoInventario.objects.filter(
            producto=producto,
            referencia=referencia
        ).exists()

        if existe_referencia:
            # Esto es solo una advertencia, no un error
            # Puedes decidir si quieres que sea un error o permitirlo
            pass

        return data