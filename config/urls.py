# config/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

# Importar la vista personalizada
from apps.usuarios.serializers.jwt import CustomTokenObtainPairView, CustomLogoutView

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # JWT Authentication (Con vista personalizada)
    path("api/token/", CustomTokenObtainPairView.as_view()),
    path("api/token/logout/", CustomLogoutView.as_view()),
    path("api/token/refresh/", TokenRefreshView.as_view()),
    path("api/token/verify/", TokenVerifyView.as_view()),
    # API Endpoints
    path("api/", include("apps.usuarios.urls")),
    path("api/categorias/", include("apps.categorias.urls", )),
    path("api/productos/", include("apps.productos.urls",)),
    path("api/inventario/", include("apps.inventario.urls", )),
    path("api/ventas/", include("apps.ventas.urls")),
    path("api/compras/", include("apps.compras.urls")),
    path("api/clientes/", include("apps.clientes.urls")),
    path("api/proveedores/", include("apps.proveedores.urls")),
    path("api/documentos/", include("apps.documentos.urls" , )),
    path("api/dashboard/", include("apps.dashboard.urls",)),
    path("api/configuracion/", include("apps.configuracion.urls")),
    path("api/auditorias/", include("apps.auditorias.urls", )),
    path("api/caja/", include("apps.caja.urls")),
    path("api/precios/", include("apps.precios.urls")),
]

# Servir archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
