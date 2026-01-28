# apps/usuarios/services/usuario_service.py
from django.db import transaction
from apps.usuarios.models import Usuario, Rol, UsuarioRol


class UsuarioService:
    """Servicio para manejar la lógica de negocio de usuarios"""
    @staticmethod
    @transaction.atomic
    def crear_usuario(username, email, password, is_active=True, roles_ids=None):
        """
        Crear un nuevo usuario con roles

        Args:
            username: Nombre de usuario
            email: Email del usuario
            password: Contraseña del usuario
            is_active: Si el usuario está activo
            roles_ids: Lista de IDs de roles a asignar

        Returns:
            Usuario: Instancia del usuario creado
        """
        # Crear usuario
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_active=is_active
        )

        # Asignar roles
        if roles_ids:
            roles = Rol.objects.filter(id__in=roles_ids)
            for rol in roles:
                UsuarioRol.objects.create(usuario=usuario, rol=rol)

        return usuario

    @staticmethod
    @transaction.atomic
    def actualizar_usuario(usuario_id, **kwargs):
        """
        Actualizar un usuario existente

        Args:
            usuario_id: ID del usuario a actualizar
            **kwargs: Campos a actualizar (username, email, is_active, roles_ids)

        Returns:
            Usuario: Instancia del usuario actualizado
        """
        usuario = Usuario.objects.get(id=usuario_id)

        # Actualizar campos básicos
        if 'username' in kwargs:
            usuario.username = kwargs['username']
        if 'email' in kwargs:
            usuario.email = kwargs['email']
        if 'is_active' in kwargs:
            usuario.is_active = kwargs['is_active']

        usuario.save()

        # Actualizar roles si se proporcionan
        if 'roles_ids' in kwargs:
            roles_ids = kwargs['roles_ids']
            # Eliminar roles existentes
            UsuarioRol.objects.filter(usuario=usuario).delete()
            # Agregar nuevos roles
            if roles_ids:
                roles = Rol.objects.filter(id__in=roles_ids)
                for rol in roles:
                    UsuarioRol.objects.create(usuario=usuario, rol=rol)

        return usuario

    @staticmethod
    def cambiar_password(usuario, old_password, new_password):
        """
        Cambiar la contraseña de un usuario
        
        Args:
            usuario: Instancia del usuario
            old_password: Contraseña actual
            new_password: Nueva contraseña
        
        Returns:
            bool: True si se cambió exitosamente
        
        Raises:
            ValueError: Si la contraseña actual es incorrecta
        """
        if not usuario.check_password(old_password):
            raise ValueError("La contraseña actual es incorrecta")
        
        usuario.set_password(new_password)
        usuario.save()
        return True
    
    @staticmethod
    def activar_usuario(usuario_id):
        """Activar un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.is_active = True
        usuario.save()
        return usuario
    
    @staticmethod
    def desactivar_usuario(usuario_id):
        """Desactivar un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        usuario.is_active = False
        usuario.save()
        return usuario

    @staticmethod
    def obtener_estadisticas_usuario(usuario_id):
        """
        Obtener estadísticas de un usuario

        Args:
            usuario_id: ID del usuario

        Returns:
            dict: Diccionario con estadísticas del usuario
        """
        usuario = Usuario.objects.get(id=usuario_id)

        estadisticas = {
            'id': usuario.id,
            'username': usuario.username,
            'email': usuario.email,
            'is_active': usuario.is_active,
            'total_ventas': usuario.ventas.count() if hasattr(usuario, 'ventas') else 0,
            'total_compras': usuario.compras.count() if hasattr(usuario, 'compras') else 0,
            'ventas_completadas': usuario.ventas.filter(estado='COMPLETADA').count() if hasattr(usuario, 'ventas') else 0,
            'ventas_pendientes': usuario.ventas.filter(estado='PENDIENTE').count() if hasattr(usuario, 'ventas') else 0,
            'roles': [ur.rol.nombre for ur in usuario.usuario_roles.all()],
            'fecha_creacion': usuario.fecha_creacion,
            'ultimo_login': usuario.last_login
        }

        return estadisticas

    @staticmethod
    def asignar_rol(usuario_id, rol_id):
        """Asignar un rol a un usuario"""
        usuario = Usuario.objects.get(id=usuario_id)
        rol = Rol.objects.get(id=rol_id)

        # Verificar si ya tiene el rol
        if not UsuarioRol.objects.filter(usuario=usuario, rol=rol).exists():
            UsuarioRol.objects.create(usuario=usuario, rol=rol)

        return usuario

    @staticmethod
    def remover_rol(usuario_id, rol_id):
        """Remover un rol de un usuario"""
        UsuarioRol.objects.filter(usuario_id=usuario_id, rol_id=rol_id).delete()
        return Usuario.objects.get(id=usuario_id)


class RolService:
    """Servicio para manejar la lógica de negocio de roles"""

    @staticmethod
    def crear_rol(nombre, descripcion=None):
        """Crear un nuevo rol"""
        rol = Rol.objects.create(nombre=nombre, descripcion=descripcion)
        return rol

    @staticmethod
    def actualizar_rol(rol_id, nombre=None, descripcion=None):
        """Actualizar un rol existente"""
        rol = Rol.objects.get(id=rol_id)

        if nombre:
            rol.nombre = nombre
        if descripcion is not None:
            rol.descripcion = descripcion

        rol.save()
        return rol

    @staticmethod
    def eliminar_rol(rol_id):
        """Eliminar un rol"""
        rol = Rol.objects.get(id=rol_id)
        rol.delete()
    
    @staticmethod
    def obtener_usuarios_por_rol(rol_id):
        """Obtener todos los usuarios que tienen un rol específico"""
        return Usuario.objects.filter(usuario_roles__rol_id=rol_id)