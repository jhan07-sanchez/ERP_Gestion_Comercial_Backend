# apps/usuarios/views/api.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q

from apps.usuarios.models import Usuario, Rol
from apps.usuarios.serializers import (
    # Read
    RolReadSerializer,
    UsuarioListSerializer,
    UsuarioDetailSerializer,
    UsuarioMeSerializer,
    # Write
    RolWriteSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    ChangePasswordSerializer,
    UsuarioActivateSerializer
)
from apps.usuarios.services import UsuarioService, RolService


class RolViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar roles

    list: GET /api/roles/ - Listar todos los roles
    create: POST /api/roles/ - Crear un nuevo rol
    retrieve: GET /api/roles/{id}/ - Obtener detalle de un rol
    update: PUT /api/roles/{id}/ - Actualizar un rol completo
    partial_update: PATCH /api/roles/{id}/ - Actualizar parcialmente un rol
    destroy: DELETE /api/roles/{id}/ - Eliminar un rol
    usuarios: GET /api/roles/{id}/usuarios/ - Obtener usuarios con este rol
    """
    queryset = Rol.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action in ['create', 'update', 'partial_update']:
            return RolWriteSerializer
        return RolReadSerializer

    def get_queryset(self):
        """Filtrar roles según parámetros"""
        queryset = Rol.objects.all()

        # Búsqueda por nombre
        nombre = self.request.query_params.get('nombre', None)
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)

        # Búsqueda por descripción
        descripcion = self.request.query_params.get('descripcion', None)
        if descripcion:
            queryset = queryset.filter(descripcion__icontains=descripcion)

        # Búsqueda general (nombre o descripción)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )

        return queryset.order_by('nombre')

    def create(self, request, *args, **kwargs):
        """Crear un nuevo rol usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rol = RolService.crear_rol(
                nombre=serializer.validated_data['nombre'],
                descripcion=serializer.validated_data.get('descripcion')
            )

            response_serializer = RolReadSerializer(rol)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Actualizar un rol usando el servicio"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            rol = RolService.actualizar_rol(
                rol_id=instance.id,
                nombre=serializer.validated_data.get('nombre'),
                descripcion=serializer.validated_data.get('descripcion')
            )

            response_serializer = RolReadSerializer(rol)
            return Response(response_serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Eliminar un rol"""
        instance = self.get_object()

        # Verificar si hay usuarios con este rol
        usuarios_con_rol = instance.usuario_roles.count()
        if usuarios_con_rol > 0:
            return Response(
                {
                    'error': f'No se puede eliminar el rol porque {usuarios_con_rol} usuario(s) lo tienen asignado.'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            RolService.eliminar_rol(instance.id)
            return Response(
                {'detail': 'Rol eliminado exitosamente.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def usuarios(self, request, pk=None):
        """
        Obtener todos los usuarios que tienen este rol

        GET /api/roles/{id}/usuarios/
        """
        rol = self.get_object()
        usuarios = RolService.obtener_usuarios_por_rol(rol.id)
        serializer = UsuarioListSerializer(usuarios, many=True)

        return Response({
            'rol': rol.nombre,
            'total_usuarios': usuarios.count(),
            'usuarios': serializer.data
        })


class UsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios

    list: GET /api/usuarios/ - Listar todos los usuarios
    create: POST /api/usuarios/ - Crear un nuevo usuario
    retrieve: GET /api/usuarios/{id}/ - Obtener detalle de un usuario
    update: PUT /api/usuarios/{id}/ - Actualizar un usuario completo
    partial_update: PATCH /api/usuarios/{id}/ - Actualizar parcialmente un usuario
    destroy: DELETE /api/usuarios/{id}/ - Eliminar un usuario
    me: GET /api/usuarios/me/ - Obtener información del usuario autenticado
    change_password: POST /api/usuarios/{id}/change_password/ - Cambiar contraseña
    activate: POST /api/usuarios/{id}/activate/ - Activar usuario
    deactivate: POST /api/usuarios/{id}/deactivate/ - Desactivar usuario
    estadisticas: GET /api/usuarios/{id}/estadisticas/ - Obtener estadísticas
    asignar_rol: POST /api/usuarios/{id}/asignar_rol/ - Asignar un rol
    remover_rol: POST /api/usuarios/{id}/remover_rol/ - Remover un rol
    """
    queryset = Usuario.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == 'create':
            return UsuarioCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        elif self.action == 'retrieve':
            return UsuarioDetailSerializer
        elif self.action == 'me':
            return UsuarioMeSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        elif self.action in ['activate', 'deactivate']:
            return UsuarioActivateSerializer
        return UsuarioListSerializer

    def get_permissions(self):
        """Permitir registro público de usuarios"""
        if self.action == 'create':
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Filtrar usuarios según parámetros"""
        queryset = Usuario.objects.select_related().prefetch_related(
            'usuario_roles__rol',
            'ventas',
            'compras'
        )

        # Filtro por username
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(username__icontains=username)

        # Filtro por email
        email = self.request.query_params.get('email', None)
        if email:
            queryset = queryset.filter(email__icontains=email)

        # Filtro por estado activo
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filtro por rol
        rol = self.request.query_params.get('rol', None)
        if rol:
            queryset = queryset.filter(usuario_roles__rol__nombre__icontains=rol)

        # Filtro por staff
        is_staff = self.request.query_params.get('is_staff', None)
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff.lower() == 'true')

        # Búsqueda general (username o email)
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) | Q(email__icontains=search)
            )

        return queryset.distinct().order_by('-fecha_creacion')

    def create(self, request, *args, **kwargs):
        """Crear un nuevo usuario usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            usuario = UsuarioService.crear_usuario(
                username=serializer.validated_data['username'],
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password'],
                is_active=serializer.validated_data.get('is_active', True),
                roles_ids=serializer.validated_data.get('roles_ids', [])
            )

            response_serializer = UsuarioDetailSerializer(usuario)
            return Response(
                response_serializer.data,
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def update(self, request, *args, **kwargs):
        """Actualizar un usuario usando el servicio"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            usuario = UsuarioService.actualizar_usuario(
                usuario_id=instance.id,
                username=serializer.validated_data.get('username'),
                email=serializer.validated_data.get('email'),
                is_active=serializer.validated_data.get('is_active'),
                roles_ids=serializer.validated_data.get('roles_ids')
            )

            response_serializer = UsuarioDetailSerializer(usuario)
            return Response(response_serializer.data)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """Eliminar (desactivar) un usuario"""
        instance = self.get_object()

        # No eliminar físicamente, solo desactivar
        try:
            UsuarioService.desactivar_usuario(instance.id)
            return Response(
                {'detail': 'Usuario desactivado exitosamente.'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Obtener información del usuario autenticado

        GET /api/usuarios/me/
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def change_password(self, request, pk=None):
        """
        Cambiar contraseña de un usuario

        POST /api/usuarios/{id}/change_password/
        Body: {
            "old_password": "password_actual",
            "new_password": "nueva_password",
            "new_password2": "nueva_password"
        }
        """
        usuario = self.get_object()

        # Solo el mismo usuario puede cambiar su contraseña (o un admin)
        if request.user.id != usuario.id and not request.user.is_staff:
            return Response(
                {'error': 'No tienes permiso para cambiar esta contraseña.'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            try:
                UsuarioService.cambiar_password(
                    usuario=request.user,
                    old_password=serializer.validated_data['old_password'],
                    new_password=serializer.validated_data['new_password']
                )
                return Response(
                    {'detail': 'Contraseña cambiada exitosamente.'},
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def activate(self, request, pk=None):
        """
        Activar un usuario

        POST /api/usuarios/{id}/activate/
        """
        try:
            usuario = UsuarioService.activar_usuario(pk)
            return Response(
                {
                    'detail': f'Usuario {usuario.username} activado exitosamente.',
                    'usuario': UsuarioDetailSerializer(usuario).data
                },
                status=status.HTTP_200_OK
            )
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def deactivate(self, request, pk=None):
        """
        Desactivar un usuario

        POST /api/usuarios/{id}/deactivate/
        """
        try:
            usuario = UsuarioService.desactivar_usuario(pk)
            return Response(
                {
                    'detail': f'Usuario {usuario.username} desactivado exitosamente.',
                    'usuario': UsuarioDetailSerializer(usuario).data
                },
                status=status.HTTP_200_OK
            )
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas del usuario

        GET /api/usuarios/{id}/estadisticas/
        """
        try:
            estadisticas = UsuarioService.obtener_estadisticas_usuario(pk)
            return Response(estadisticas, status=status.HTTP_200_OK)
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def asignar_rol(self, request, pk=None):
        """
        Asignar un rol a un usuario

        POST /api/usuarios/{id}/asignar_rol/
        Body: {
            "rol_id": 1
        }
        """
        rol_id = request.data.get('rol_id')

        if not rol_id:
            return Response(
                {'error': 'El campo rol_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            usuario = UsuarioService.asignar_rol(pk, rol_id)
            return Response(
                {
                    'detail': 'Rol asignado exitosamente.',
                    'usuario': UsuarioDetailSerializer(usuario).data
                },
                status=status.HTTP_200_OK
            )
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Rol.DoesNotExist:
            return Response(
                {'error': 'Rol no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def remover_rol(self, request, pk=None):
        """
        Remover un rol de un usuario

        POST /api/usuarios/{id}/remover_rol/
        Body: {
            "rol_id": 1
        }
        """
        rol_id = request.data.get('rol_id')

        if not rol_id:
            return Response(
                {'error': 'El campo rol_id es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            usuario = UsuarioService.remover_rol(pk, rol_id)
            return Response(
                {
                    'detail': 'Rol removido exitosamente.',
                    'usuario': UsuarioDetailSerializer(usuario).data
                },
                status=status.HTTP_200_OK
            )
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'Usuario no encontrado.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )