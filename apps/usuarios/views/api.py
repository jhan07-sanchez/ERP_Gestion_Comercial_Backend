# apps/usuarios/views/api.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Q
from apps.auditorias.mixins import MixinAuditable
from apps.auditorias.services.auditoria_service import AuditoriaService
from apps.auditorias.utils import snapshot_objeto

from apps.usuarios.serializers.write import (
    # Write
    RolWriteSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer,
    ChangePasswordSerializer,
    UsuarioActivateSerializer,
    SolicitudCuentaCreateSerializer,
    ActivarCuentaSerializer
)
from apps.usuarios.serializers.read import (
    # Read
    RolReadSerializer,
    UsuarioListSerializer,
    UsuarioDetailSerializer,
    UsuarioMeSerializer
)
from apps.usuarios.models import Usuario, Rol, SolicitudCuenta
from apps.usuarios.services import UsuarioService, RolService
from apps.usuarios.services.saas_service import SaaSAccountService


class RolViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet para gestionar roles
    """
    queryset = Rol.objects.all()
    permission_classes = [IsAuthenticated]
    modulo_auditoria = 'USUARIOS'

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
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='CREAR',
                modulo=self.modulo_auditoria,
                objeto=rol,
                descripcion=f"Rol creado: {rol.nombre}",
                request=request,
                datos_despues=snapshot_objeto(rol)
            )

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

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=rol,
                descripcion=f"Rol actualizado: {rol.nombre}",
                request=request,
                datos_antes=snapshot_objeto(instance),
                datos_despues=snapshot_objeto(rol)
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


class UsuarioViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet para gestionar usuarios
    """
    queryset = Usuario.objects.all()
    permission_classes = [IsAuthenticated]
    modulo_auditoria = 'USUARIOS'

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

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user if request.user.is_authenticated else None,
                accion='CREAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Usuario creado: {usuario.username} ({usuario.email})",
                request=request,
                datos_despues=snapshot_objeto(usuario)
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

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Usuario actualizado: {usuario.username}",
                request=request,
                datos_antes=snapshot_objeto(instance),
                datos_despues=snapshot_objeto(usuario)
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
            datos_antes = snapshot_objeto(instance)
            UsuarioService.desactivar_usuario(instance.id)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ELIMINAR', # Se registra como eliminar por ser el método destroy
                modulo=self.modulo_auditoria,
                objeto=instance,
                descripcion=f"Usuario desactivado vía destroy: {instance.username}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(instance)
            )

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

                # Auditoría
                AuditoriaService.registrar_accion(
                    usuario=request.user,
                    accion='ACTUALIZAR',
                    modulo='SISTEMA',
                    objeto=usuario,
                    descripcion=f"Contraseña cambiada para el usuario: {usuario.username}",
                    request=request
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
            instance = Usuario.objects.get(pk=pk)
            datos_antes = snapshot_objeto(instance)
            usuario = UsuarioService.activar_usuario(pk)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Usuario activado: {usuario.username}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(usuario)
            )

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
            instance = Usuario.objects.get(pk=pk)
            datos_antes = snapshot_objeto(instance)
            usuario = UsuarioService.desactivar_usuario(pk)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Usuario desactivado: {usuario.username}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(usuario)
            )

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
            instance = Usuario.objects.get(pk=pk)
            datos_antes = snapshot_objeto(instance)
            usuario = UsuarioService.asignar_rol(pk, rol_id)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Rol asignado a usuario {usuario.username}. ID Rol: {rol_id}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(usuario)
            )

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
            instance = Usuario.objects.get(pk=pk)
            datos_antes = snapshot_objeto(instance)
            usuario = UsuarioService.remover_rol(pk, rol_id)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo=self.modulo_auditoria,
                objeto=usuario,
                descripcion=f"Rol removido de usuario {usuario.username}. ID Rol: {rol_id}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(usuario)
            )

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
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class SolicitudCuentaViewSet(viewsets.GenericViewSet):
    """
    ViewSet para manejar solicitudes de cuenta.
    Público para permitir a cualquier persona registrarse.
    """
    permission_classes = [AllowAny]
    serializer_class = SolicitudCuentaCreateSerializer

    @action(detail=False, methods=['post'], url_path='solicitar-cuenta')
    def solicitar_cuenta(self, request):
        """
        POST /api/auth/solicitar-cuenta/
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            solicitud = serializer.save()
            return Response(
                {
                    "message": "Solicitud enviada correctamente. Un administrador la revisará pronto.",
                    "solicitud_id": solicitud.id
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def aprobar(self, request, pk=None):
        """
        POST /api/auth/{id}/aprobar/
        Permite a un administrador del sistema aprobar una solicitud.
        """
        if not request.user.is_staff:
            return Response({"error": "No tienes permisos para aprobar solicitudes."}, status=status.HTTP_403_FORBIDDEN)
            
        try:
            usuario, empresa = SaaSAccountService.aprobar_solicitud(pk)
            return Response({
                "message": f"Solicitud aprobada. Se creó la empresa {empresa.nombre} y el usuario {usuario.email}.",
                "usuario_id": usuario.id,
                "empresa_id": empresa.id
            }, status=status.HTTP_200_OK)
        except SolicitudCuenta.DoesNotExist:
            return Response({"error": "Solicitud no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='activar-cuenta')
    def activar_cuenta(self, request):
        """
        POST /api/auth/activar-cuenta/
        """
        serializer = ActivarCuentaSerializer(data=request.data)
        if serializer.is_valid():
            try:
                usuario = SaaSAccountService.activar_cuenta(
                    token_uuid=serializer.validated_data['token'],
                    new_password=serializer.validated_data['password']
                )
                return Response(
                    {
                        "message": "Cuenta activada exitosamente. Tu período de prueba ha iniciado.",
                        "usuario": usuario.email
                    },
                    status=status.HTTP_200_OK
                )
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)