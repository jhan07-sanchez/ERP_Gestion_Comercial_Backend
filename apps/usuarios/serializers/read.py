# apps/usuarios/serializers/read.py
from rest_framework import serializers
from apps.usuarios.models import Usuario, Rol, UsuarioRol


class RolReadSerializer(serializers.ModelSerializer):
    """Serializer para leer roles"""
    
    class Meta:
        model = Rol
        fields = [
            'id',
            'nombre',
            'descripcion',
            'fecha_creacion',
            'fecha_actualizacion'
        ]


class UsuarioRolReadSerializer(serializers.ModelSerializer):
    """Serializer para leer la relación Usuario-Rol"""
    rol_nombre = serializers.CharField(source='rol.nombre', read_only=True)
    rol_descripcion = serializers.CharField(source='rol.descripcion', read_only=True)

    class Meta:
        model = UsuarioRol
        fields = ['id', 'rol', 'rol_nombre', 'rol_descripcion']


class UsuarioListSerializer(serializers.ModelSerializer):
    """Serializer para listar usuarios (vista resumida)"""
    roles = UsuarioRolReadSerializer(source='usuario_roles', many=True, read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'email',
            'is_active',
            'is_staff',
            'roles',
            'fecha_creacion'
        ]


class UsuarioDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalle de usuario (vista completa)"""
    roles = UsuarioRolReadSerializer(source='usuario_roles', many=True, read_only=True)
    total_ventas = serializers.SerializerMethodField()
    total_compras = serializers.SerializerMethodField()
    total_movimientos_inventario = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'roles',
            'total_ventas',
            'total_compras',
            'total_movimientos_inventario',
            'last_login',
            'fecha_creacion',
            'fecha_actualizacion'
        ]
    
    def get_total_ventas(self, obj):
        """Obtener total de ventas del usuario"""
        return obj.ventas.count() if hasattr(obj, 'ventas') else 0
    
    def get_total_compras(self, obj):
        """Obtener total de compras del usuario"""
        return obj.compras.count() if hasattr(obj, 'compras') else 0
    
    def get_total_movimientos_inventario(self, obj):
        """Obtener total de movimientos de inventario"""
        return obj.movimientos_inventario.count() if hasattr(obj, 'movimientos_inventario') else 0


class UsuarioMeSerializer(serializers.ModelSerializer):
    """Serializer para el usuario autenticado (perfil)"""
    roles = UsuarioRolReadSerializer(source='usuario_roles', many=True, read_only=True)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'roles',
            'permisos',
            'last_login',
            'fecha_creacion'
        ]
    
    def get_permisos(self, obj):
        """Obtener permisos del usuario"""
        permisos = []
        for rol in obj.usuario_roles.all():
            permisos.append(rol.rol.nombre)
        return permisos