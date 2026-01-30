# apps/clientes/serializers/write.py
"""
Serializers de ESCRITURA para Clientes

Este archivo contiene los serializers para:
- Crear datos de clientes (POST requests)
- Actualizar datos (PUT/PATCH requests)
- Validaciones específicas de escritura

Autor: Sistema ERP
Fecha: 2026-01-29
"""

from rest_framework import serializers
from apps.clientes.models import Cliente
import re


# ============================================================================
# SERIALIZERS DE CLIENTE (WRITE)
# ============================================================================

class ClienteCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR clientes
    
    Usado en:
    - POST /api/clientes/
    
    Validaciones:
    - Nombre: Mínimo 3 caracteres
    - Documento: Único, solo números
    - Email: Formato válido, único
    - Teléfono: Solo números (opcional)
    """
    
    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'documento',
            'telefono',
            'email',
            'direccion',
            'estado'
        ]
    
    def validate_nombre(self, value):
        """Validar nombre del cliente"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 200:
            raise serializers.ValidationError(
                "El nombre no puede tener más de 200 caracteres."
            )
        return value.strip()
    
    def validate_documento(self, value):
        """
        Validar documento del cliente
        
        Reglas:
        - Debe ser único
        - Solo números
        - Mínimo 5 caracteres
        """
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "El documento debe tener al menos 5 caracteres."
            )
        
        # Limpiar espacios
        documento_limpio = value.strip().replace(' ', '')
        
        # Validar que solo contenga números (permitir guiones para algunos tipos de docs)
        if not re.match(r'^[0-9-]+$', documento_limpio):
            raise serializers.ValidationError(
                "El documento solo puede contener números y guiones."
            )
        
        # Validar unicidad
        if Cliente.objects.filter(documento=documento_limpio).exists():
            raise serializers.ValidationError(
                "Ya existe un cliente con este documento."
            )
        
        return documento_limpio
    
    def validate_telefono(self, value):
        """Validar teléfono (opcional)"""
        if value:
            # Limpiar espacios y caracteres especiales
            telefono_limpio = value.strip().replace(' ', '').replace('-', '').replace('+', '')
            
            if not re.match(r'^[0-9]+$', telefono_limpio):
                raise serializers.ValidationError(
                    "El teléfono solo puede contener números."
                )
            
            if len(telefono_limpio) < 7:
                raise serializers.ValidationError(
                    "El teléfono debe tener al menos 7 dígitos."
                )
            
            if len(telefono_limpio) > 20:
                raise serializers.ValidationError(
                    "El teléfono no puede tener más de 20 dígitos."
                )
            
            return telefono_limpio
        
        return value
    
    def validate_email(self, value):
        """Validar email (opcional pero debe ser único si se proporciona)"""
        if value:
            # Django ya valida el formato con EmailField
            # Solo validamos unicidad
            if Cliente.objects.filter(email=value.lower()).exists():
                raise serializers.ValidationError(
                    "Ya existe un cliente con este email."
                )
            return value.lower()
        
        return value


class ClienteUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR clientes
    
    Usado en:
    - PUT/PATCH /api/clientes/{id}/
    
    Nota: El documento no se puede modificar una vez creado
    """
    documento = serializers.CharField(read_only=True)
    
    class Meta:
        model = Cliente
        fields = [
            'nombre',
            'documento',  # read_only
            'telefono',
            'email',
            'direccion',
            'estado'
        ]
    
    def validate_nombre(self, value):
        """Validar nombre del cliente"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 200:
            raise serializers.ValidationError(
                "El nombre no puede tener más de 200 caracteres."
            )
        return value.strip()
    
    def validate_telefono(self, value):
        """Validar teléfono"""
        if value:
            telefono_limpio = value.strip().replace(' ', '').replace('-', '').replace('+', '')
            
            if not re.match(r'^[0-9]+$', telefono_limpio):
                raise serializers.ValidationError(
                    "El teléfono solo puede contener números."
                )
            
            if len(telefono_limpio) < 7:
                raise serializers.ValidationError(
                    "El teléfono debe tener al menos 7 dígitos."
                )
            
            return telefono_limpio
        
        return value
    
    def validate_email(self, value):
        """Validar email (debe ser único excepto el actual)"""
        if value:
            # Validar unicidad (excepto el cliente actual)
            if self.instance:
                if Cliente.objects.exclude(id=self.instance.id).filter(email=value.lower()).exists():
                    raise serializers.ValidationError(
                        "Ya existe otro cliente con este email."
                    )
            return value.lower()
        
        return value


class ClienteActivateSerializer(serializers.Serializer):
    """
    Serializer para ACTIVAR/DESACTIVAR clientes
    
    Usado en:
    - POST /api/clientes/{id}/activar/
    - POST /api/clientes/{id}/desactivar/
    """
    estado = serializers.BooleanField(required=True)