# apps/proveedores/serializers/write.py
"""
Serializers de ESCRITURA para Proveedores

Este archivo contiene los serializers para:
- Crear datos de proveedores (POST requests)
- Actualizar datos (PUT/PATCH requests)
- Validaciones específicas de escritura

Autor: Sistema ERP
Fecha: 2026-02-06
"""

from rest_framework import serializers
from apps.proveedores.models import Proveedor
import re


# ============================================================================
# SERIALIZERS DE PROVEEDOR (WRITE)
# ============================================================================

class ProveedorCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para CREAR proveedores
    
    Usado en:
    - POST /api/proveedores/
    
    Validaciones:
    - Nombre: Mínimo 3 caracteres
    - Documento: Único, solo números
    - Email: Formato válido, único (opcional)
    - Teléfono: Solo números (opcional)
    """
    
    class Meta:
        model = Proveedor
        fields = [
            'nombre',
            'documento',
            'telefono',
            'email',
            'direccion',
            'activo'
        ]
    
    def validate_nombre(self, value):
        """Validar nombre del proveedor"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 150:
            raise serializers.ValidationError(
                "El nombre no puede tener más de 150 caracteres."
            )
        return value.strip()
    
    def validate_documento(self, value):
        """
        Validar documento del proveedor
        
        Reglas:
        - Debe ser único
        - Solo números y guiones
        - Mínimo 5 caracteres
        """
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError(
                "El documento debe tener al menos 5 caracteres."
            )
        
        # Limpiar espacios
        documento_limpio = value.strip().replace(' ', '')
        
        # Validar que solo contenga números (permitir guiones para NIT)
        if not re.match(r'^[0-9-]+$', documento_limpio):
            raise serializers.ValidationError(
                "El documento solo puede contener números y guiones."
            )
        
        # Validar unicidad
        if Proveedor.objects.filter(documento=documento_limpio).exists():
            raise serializers.ValidationError(
                "Ya existe un proveedor con este documento."
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
            
            if len(telefono_limpio) > 30:
                raise serializers.ValidationError(
                    "El teléfono no puede tener más de 30 dígitos."
                )
            
            return telefono_limpio
        
        return value
    
    def validate_email(self, value):
        """Validar email (opcional pero debe ser único si se proporciona)"""
        if value:
            # Django ya valida el formato con EmailField
            # Solo validamos unicidad
            if Proveedor.objects.filter(email=value.lower()).exists():
                raise serializers.ValidationError(
                    "Ya existe un proveedor con este email."
                )
            return value.lower()
        
        return value


class ProveedorUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer para ACTUALIZAR proveedores
    
    Usado en:
    - PUT/PATCH /api/proveedores/{id}/
    
    Nota: El documento no se puede modificar una vez creado
    """
    documento = serializers.CharField(read_only=True)
    
    class Meta:
        model = Proveedor
        fields = [
            'nombre',
            'documento',  # read_only
            'telefono',
            'email',
            'direccion',
            'activo'
        ]
    
    def validate_nombre(self, value):
        """Validar nombre del proveedor"""
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError(
                "El nombre debe tener al menos 3 caracteres."
            )
        if len(value) > 150:
            raise serializers.ValidationError(
                "El nombre no puede tener más de 150 caracteres."
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
            # Validar unicidad (excepto el proveedor actual)
            if self.instance:
                if Proveedor.objects.exclude(id=self.instance.id).filter(email=value.lower()).exists():
                    raise serializers.ValidationError(
                        "Ya existe otro proveedor con este email."
                    )
            return value.lower()
        
        return value


class ProveedorActivateSerializer(serializers.Serializer):
    """
    Serializer para ACTIVAR/DESACTIVAR proveedores
    
    Usado en:
    - POST /api/proveedores/{id}/activar/
    - POST /api/proveedores/{id}/desactivar/
    """
    activo = serializers.BooleanField(required=True)