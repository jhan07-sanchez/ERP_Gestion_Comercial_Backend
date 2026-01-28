# apps/usuarios/serializers/jwt.py
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


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
    """Vista personalizada para obtener token"""
    serializer_class = CustomTokenObtainPairSerializer