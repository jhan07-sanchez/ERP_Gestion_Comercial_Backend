from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.precios.views.api import ListaPrecioCompraViewSet

app_name = "precio"

router = DefaultRouter()
router.register(r"precios", ListaPrecioCompraViewSet, basename="precio")

urlpatterns = [
    path("", include(router.urls)),
]
