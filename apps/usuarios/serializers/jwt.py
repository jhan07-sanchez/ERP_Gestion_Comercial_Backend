# apps/usuarios/serializers/jwt.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.auditorias.services.auditoria_service import AuditoriaService
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Serializer personalizado para obtener token con email en lugar de username
    """
    username_field = 'email'  # Cambiar de username a email
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Agregar información adicional al token
        token['username'] = user.username
        token['email'] = user.email
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        
        return token
    
    def validate(self, attrs):
        """Validar credenciales y retornar información del usuario"""
        data = super().validate(attrs)
        
        # Agregar información adicional en la respuesta
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'is_active': self.user.is_active,
            'is_staff': self.user.is_staff,
        }
        
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    """Vista personalizada para obtener token y registrar auditoría"""
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Intentamos obtener el token normal
        try:
            response = super().post(request, *args, **kwargs)
            
            # Si fue exitoso, el serializer.validated_data ya debe tener info
            serializer = self.get_serializer(data=request.data)
            try:
                serializer.is_valid(raise_exception=True)
                usuario = serializer.user
                
                # Registrar auditoría de Login Exitoso
                AuditoriaService.registrar_accion(
                    usuario=usuario,
                    accion='LOGIN',
                    modulo='USUARIOS',
                    descripcion=f"Inicio de sesión exitoso: {usuario.get_full_name() or usuario.username}",
                    request=request
                )
            except Exception:
                pass # Falló algo al sacar el user, pero el login fue exitoso. Extraño.

            return response
            
        except Exception as e:
            # Login Fallido
            email_intento = request.data.get('email', 'desconocido')
            AuditoriaService.registrar_accion(
                usuario=None,
                accion='LOGIN_FALLIDO',
                modulo='USUARIOS',
                descripcion=f"Intento de login fallido para email: {email_intento}. Razón: {str(e)}",
                request=request,
                extra={"email_intento": email_intento}
            )
            # Re-lanzar la excepción original para que DRF maneje el error 401
            raise e

class CustomLogoutView(APIView):
    """Vista para registrar logout de manera explícita en Auditoría"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Registrar Logout
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='LOGOUT',
                modulo='USUARIOS',
                descripcion=f"Cierre de sesión: {request.user.get_full_name() or request.user.username}",
                request=request
            )
            return Response({"detail": "Logout registrado exitosamente."}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
