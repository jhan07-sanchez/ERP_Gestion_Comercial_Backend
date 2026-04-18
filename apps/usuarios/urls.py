# apps/usuarios/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.usuarios.views.api import UsuarioViewSet, RolViewSet, SolicitudCuentaViewSet

app_name = 'usuarios'

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')
router.register(r'roles', RolViewSet, basename='rol')
router.register(r'auth', SolicitudCuentaViewSet, basename='auth')

urlpatterns = [
    path('', include(router.urls)),
]