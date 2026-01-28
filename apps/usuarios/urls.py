# apps/usuarios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.usuarios.views import UsuarioViewSet, RolViewSet

app_name = 'usuarios'

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'roles', RolViewSet, basename='rol')

urlpatterns = [
    path('', include(router.urls)),
]