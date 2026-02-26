# apps/categorias/serializers/read.py
"""
Serializers de LECTURA para Categorías

Este archivo contiene los serializers para:
- Leer datos (GET requests)
- Mostrar información en listas y detalles
- Incluir datos relacionados y calculados

Separados de los serializers de escritura para:
- Mayor claridad en el código
- Validaciones específicas para cada operación
- Mejor organización
"""

from rest_framework import serializers
from apps.categorias.models import Categoria


# ============================================================================
# SERIALIZERS DE CATEGORÍA (READ)
# ============================================================================

class CategoriaReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Categorías

    Usado en:
    - GET /api/categorias/ (lista)
    - GET /api/categorias/{id}/ (detalle)

    Incluye:
    - Información completa de la categoría
    - Total de productos en la categoría
    - Total de productos activos
    """
    total_productos = serializers.SerializerMethodField()
    productos_activos = serializers.SerializerMethodField()

    class Meta:
        model = Categoria
        fields = [
            'id',
            'nombre',
            'descripcion',
            'total_productos',
            'productos_activos',
            'fecha_creacion',
            'fecha_actualizacion'
        ]

    def get_total_productos(self, obj):
        """Obtener total de productos en la categoría"""
        return obj.productos.count()

    def get_productos_activos(self, obj):
        """Obtener total de productos activos"""
        return obj.productos.filter(estado=True).count()


class CategoriaSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple de categoría para usar en relaciones

    Usado en:
    - Campos anidados de otros serializers
    - Respuestas donde no se necesita toda la información
    """
    class Meta:
        model = Categoria
        fields = ['id', 'nombre']
