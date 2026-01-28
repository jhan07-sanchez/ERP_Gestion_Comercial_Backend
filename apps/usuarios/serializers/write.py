# apps/usuarios/serializers/write.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from apps.usuarios.models import Usuario, Rol, UsuarioRol


class RolWriteSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar roles"""

    class Meta:
        model = Rol
        fields = ['nombre', 'descripcion']

    def validate_nombre(self, value):
        """Validar que el nombre del rol sea único"""
        if self.instance:  # Update
            if Rol.objects.exclude(id=self.instance.id).filter(nombre=value).exists():
                raise serializers.ValidationError("Ya existe un rol con este nombre.")
        else:  # Create
            if Rol.objects.filter(nombre=value).exists():
                raise serializers.ValidationError("Ya existe un rol con este nombre.")
        return value


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear usuarios"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    roles_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Usuario
        fields = [
            'username',
            'email',
            'password',
            'password2',
            'is_active',
            'roles_ids'
        ]

    def validate_email(self, value):
        """Validar que el email sea único"""
        if Usuario.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value

    def validate_username(self, value):
        """Validar que el username sea único"""
        if Usuario.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este username.")
        return value

    def validate(self, attrs):
        """Validar que las contraseñas coincidan"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Las contraseñas no coinciden."
            })
        return attrs
    
    def validate_roles_ids(self, value):
        """Validar que los roles existan"""
        if value:
            roles_existentes = Rol.objects.filter(id__in=value).count()
            if roles_existentes != len(value):
                raise serializers.ValidationError("Uno o más roles no existen.")
        return value


class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar usuarios"""
    roles_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    
    class Meta:
        model = Usuario
        fields = [
            'username',
            'email',
            'is_active',
            'roles_ids'
        ]
    
    def validate_email(self, value):
        """Validar que el email sea único (excepto el actual)"""
        if self.instance and Usuario.objects.exclude(id=self.instance.id).filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este email.")
        return value
    
    def validate_username(self, value):
        """Validar que el username sea único (excepto el actual)"""
        if self.instance and Usuario.objects.exclude(id=self.instance.id).filter(username=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este username.")
        return value
    
    def validate_roles_ids(self, value):
        """Validar que los roles existan"""
        if value:
            roles_existentes = Rol.objects.filter(id__in=value).count()
            if roles_existentes != len(value):
                raise serializers.ValidationError("Uno o más roles no existen.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer para cambiar contraseña"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password2 = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validar que las nuevas contraseñas coincidan"""
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({
                "new_password": "Las contraseñas no coinciden."
            })
        return attrs

    def validate_old_password(self, value):
        """Validar que la contraseña actual sea correcta"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("La contraseña actual es incorrecta.")
        return value


class UsuarioActivateSerializer(serializers.Serializer):
    """Serializer para activar/desactivar usuarios"""
    is_active = serializers.BooleanField(required=True)