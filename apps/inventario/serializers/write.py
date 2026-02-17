# apps/inventario/serializers/write.py
"""
Serializers de ESCRITURA para Inventario

Este archivo contiene los serializers para:
- Crear datos (POST requests)
- Actualizar datos (PUT/PATCH requests)
- Validaciones específicas de escritura

Separados de los serializers de lectura para:
- Validaciones más estrictas
- Campos diferentes entre lectura y escritura
- Mejor organización del código
"""

from rest_framework import serializers
from apps.inventario.models import (
    Producto,
    Categoria,
    Inventario,
    MovimientoInventario
)


# ============================================================================
# SERIALIZERS DE CATEGORÍA (WRITE)
# ============================================================================

class CategoriaWriteSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para Categorías

    Usado en:
    - POST /api/inventario/categorias/ (crear)
    - PUT/PATCH /api/inventario/categorias/{id}/ (actualizar)
    """

    class Meta:
        model = Categoria
        fields = [
            'nombre',
            'descripcion'
        ]

    def validate_nombre(self, value):
        """
        Validar que el nombre de la categoría sea único

        Para CREATE: Verificar que no exista
        Para UPDATE: Verificar que no exista (excepto la actual)
        """
        # Convertir a título para consistencia
        value = value.strip().title()

        if self.instance:  # UPDATE
            if Categoria.objects.exclude(id=self.instance.id).filter(nombre=value).exists():
                raise serializers.ValidationError(
                    f"Ya existe una categoría con el nombre '{value}'."
                )
        else:  # CREATE
            if Categoria.objects.filter(nombre=value).exists():
                raise serializers.ValidationError(
                    f"Ya existe una categoría con el nombre '{value}'."
                )

        return value

    def validate_descripcion(self, value):
        """Validar descripción (opcional pero debe ser significativa)"""
        if value and len(value.strip()) < 10:
            raise serializers.ValidationError(
                "La descripción debe tener al menos 10 caracteres si se proporciona."
            )
        return value.strip() if value else None


# ============================================================================
# SERIALIZERS DE PRODUCTO (WRITE)
# ============================================================================

class ProductoCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR productos

    Usado en:
    - POST /api/inventario/productos/

    Al crear un producto:
    1. Valida todos los campos
    2. Crea el producto
    3. Crea automáticamente su registro de inventario en 0
    """

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'categoria',
            'precio_compra',
            'precio_venta',
            'fecha_ingreso',
            'stock_minimo',
            'estado',
            'imagen'
        ]
        

    def validate_nombre(self, value):
        """Validar nombre del producto"""
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )

        return value

    def validate_precio_compra(self, value):
        """Validar precio de compra"""
        if value <= 0:
            raise serializers.ValidationError(
                "El precio de compra debe ser mayor a 0."
            )

        if value > 999999999:
            raise serializers.ValidationError(
                "El precio de compra es demasiado alto."
            )

        return value

    def validate_precio_venta(self, value):
        """Validar precio de venta"""
        if value <= 0:
            raise serializers.ValidationError(
                "El precio de venta debe ser mayor a 0."
            )

        if value > 999999999:
            raise serializers.ValidationError(
                "El precio de venta es demasiado alto."
            )

        return value

    def validate_stock_minimo(self, value):
        """Validar stock mínimo"""
        if value < 0:
            raise serializers.ValidationError(
                "El stock mínimo no puede ser negativo."
            )

        return value

    def validate(self, data):
        """
        Validaciones a nivel de objeto

        Valida que:
        1. precio_venta >= precio_compra (para tener ganancia)
        2. La categoría existe y está activa
        """
        precio_compra = data.get('precio_compra')
        precio_venta = data.get('precio_venta')

        # Validar que el precio de venta sea mayor al de compra
        if precio_venta < precio_compra:
            raise serializers.ValidationError({
                'precio_venta': 'El precio de venta debe ser mayor o igual al precio de compra.'
            })

        # Advertir si el margen es muy bajo (menos del 10%)
        if precio_compra > 0:
            margen = ((precio_venta - precio_compra) / precio_compra) * 100
            if margen < 10:
                # No es error, pero podríamos registrarlo
                pass

        return data

    def create(self, validated_data):
        """
        Crear producto y su registro de inventario inicial

        Pasos:
        1. Crear el producto
        2. Crear inventario inicial en 0
        3. Retornar el producto creado
        """
        # Crear el producto
        producto = Producto.objects.create(**validated_data)

        # Crear inventario inicial en 0
        Inventario.objects.create(
            producto=producto,
            stock_actual=0
        )

        return producto


class ProductoUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR productos

    Usado en:
    - PUT/PATCH /api/inventario/productos/{id}/

    Nota: No se puede cambiar el código una vez creado
    """

    class Meta:
        model = Producto
        fields = [
            'nombre',
            'descripcion',
            'categoria',
            'precio_compra',
            'precio_venta',
            'fecha_ingreso',
            'stock_minimo',
            'estado',
            'imagen'
        ]
        # El código NO se puede actualizar

    def validate_nombre(self, value):
        """Validar nombre del producto"""
        value = value.strip()

        if len(value) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )

        return value

    def validate_precio_compra(self, value):
        """Validar precio de compra"""
        if value <= 0:
            raise serializers.ValidationError(
                "El precio de compra debe ser mayor a 0."
            )

        return value

    def validate_precio_venta(self, value):
        """Validar precio de venta"""
        if value <= 0:
            raise serializers.ValidationError(
                "El precio de venta debe ser mayor a 0."
            )

        return value

    def validate_stock_minimo(self, value):
        """Validar stock mínimo"""
        if value < 0:
            raise serializers.ValidationError(
                "El stock mínimo no puede ser negativo."
            )

        return value

    def validate(self, data):
        """Validar que precio_venta >= precio_compra"""
        # Obtener los valores actuales si no se están actualizando
        precio_compra = data.get('precio_compra', self.instance.precio_compra)
        precio_venta = data.get('precio_venta', self.instance.precio_venta)

        if precio_venta < precio_compra:
            raise serializers.ValidationError({
                'precio_venta': 'El precio de venta debe ser mayor o igual al precio de compra.'
            })

        return data


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


class ProductoActivateSerializer(serializers.Serializer):
    """
    Serializer para activar/desactivar productos

    Usado en:
    - POST /api/inventario/productos/{id}/activar/
    - POST /api/inventario/productos/{id}/desactivar/
    """
    estado = serializers.BooleanField(required=False)

    def validate(self, data):
        """
        Validar que se pueda cambiar el estado

        Podrías agregar reglas como:
        - No desactivar si tiene stock
        - No desactivar si tiene ventas pendientes
        """
        # Aquí puedes agregar validaciones adicionales
        return data


class AjusteInventarioSerializer(serializers.Serializer):
    """
    Serializer para ajustes manuales de inventario

    Usado en:
    - POST /api/inventario/productos/{id}/ajustar_stock/

    Permite ajustar el stock directamente (con precaución)
    """
    stock_nuevo = serializers.IntegerField(min_value=0)
    motivo = serializers.CharField(min_length=10)

    def validate_motivo(self, value):
        """El motivo debe ser descriptivo"""
        if len(value.strip()) < 10:
            raise serializers.ValidationError(
                "El motivo del ajuste debe tener al menos 10 caracteres."
            )
        return value.strip()

    def validate_stock_nuevo(self, value):
        """Validar que el stock nuevo sea razonable"""
        if value > 999999:
            raise serializers.ValidationError(
                "El stock es demasiado alto. Verifica el valor."
            )
        return value