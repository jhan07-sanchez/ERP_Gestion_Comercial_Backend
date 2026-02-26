# apps/categorias/serializers/write.py
"""
Serializers de ESCRITURA para Categorías

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
from apps.categorias.models import Categoria


# ============================================================================
# SERIALIZERS DE CATEGORÍA (WRITE)
# ============================================================================

class CategoriaWriteSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para Categorías

    Usado en:
    - POST /api/categorias/ (crear)
    - PUT/PATCH /api/categorias/{id}/ (actualizar)
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
