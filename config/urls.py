# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

# Importar la vista personalizada
from apps.usuarios.serializers.jwt import CustomTokenObtainPairView

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # JWT Authentication (Con vista personalizada)
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # API Endpoints
    path('api/', include('apps.usuarios.urls', namespace='usuarios')),
    path('api/inventario/', include('apps.inventario.urls', namespace='inventario')),
    path('api/ventas/', include('apps.ventas.urls', namespace='ventas')),
    path('api/compras/', include('apps.compras.urls', namespace='compras')),
    path('api/clientes/', include('apps.clientes.urls', namespace='clientes')),
    path('api/proveedores/', include('apps.proveedores.urls', namespace='proveedores')),

]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)