# apps/categorias/views/api.py
"""
ViewSets para la API de Categorías

Los ViewSets utilizan:
- Serializers (read y write)
- Services (lógica de negocio)
- Permissions (control de acceso)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.categorias.models import Categoria

from apps.categorias.serializers import (
    CategoriaReadSerializer,
    CategoriaWriteSerializer,
)

from apps.productos.serializers import (
    ProductoListSerializer,
)

from apps.categorias.services import CategoriaService

from apps.usuarios.permissions import (
    EsSupervisor,
    EsAlmacenista,
    PuedeGestionarInventario,
    PuedeEliminar,
)


# ============================================================================
# VIEWSET DE CATEGORÍAS
# ============================================================================


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de productos

    Endpoints:
    - list: GET /api/categorias/
    - create: POST /api/categorias/
    - retrieve: GET /api/categorias/{id}/
    - update: PUT /api/categorias/{id}/
    - partial_update: PATCH /api/categorias/{id}/
    - destroy: DELETE /api/categorias/{id}/
    - productos: GET /api/categorias/{id}/productos/
    - estadisticas: GET /api/categorias/{id}/estadisticas/

    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear/Editar: Almacenista o superior
    - Eliminar: Solo Supervisor o Admin
    """

    queryset = Categoria.objects.prefetch_related("productos")

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action in ["create", "update", "partial_update"]:
            return CategoriaWriteSerializer
        return CategoriaReadSerializer

    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated, EsAlmacenista]
        elif self.action in ["create", "update", "partial_update"]:
            permission_classes = [IsAuthenticated, PuedeGestionarInventario]
        elif self.action == "destroy":
            permission_classes = [IsAuthenticated, PuedeEliminar]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filtrar categorías según parámetros"""
        queryset = Categoria.objects.prefetch_related("productos")

        # Búsqueda por nombre
        nombre = self.request.query_params.get("nombre", None)
        if nombre:
            queryset = queryset.filter(nombre__icontains=nombre)

        # Búsqueda general
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search) | Q(descripcion__icontains=search)
            )

        return queryset.order_by("nombre")

    def create(self, request, *args, **kwargs):
        """Crear categoría usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            categoria = CategoriaService.crear_categoria(
                nombre=serializer.validated_data["nombre"],
                descripcion=serializer.validated_data.get("descripcion"),
                estado=serializer.validated_data.get("estado", True),
            )

            response_serializer = CategoriaReadSerializer(categoria)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualizar categoría usando el servicio"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            categoria = CategoriaService.actualizar_categoria(
                categoria_id=instance.id,
                nombre=serializer.validated_data.get("nombre"),
                descripcion=serializer.validated_data.get("descripcion"),
                estado=serializer.validated_data.get("estado"),
            )

            response_serializer = CategoriaReadSerializer(categoria)
            return Response(response_serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """Eliminar categoría usando el servicio"""
        instance = self.get_object()

        try:
            CategoriaService.eliminar_categoria(instance.id)
            return Response(
                {"detail": "Categoría eliminada exitosamente."},
                status=status.HTTP_204_NO_CONTENT,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def productos(self, request, pk=None):
        """
        Obtener todos los productos de una categoría

        GET /api/categorias/{id}/productos/
        """
        categoria = self.get_object()
        productos = categoria.productos.all()

        # Filtro por estado
        estado = request.query_params.get("estado", None)
        if estado is not None:
            productos = productos.filter(estado=estado.lower() == "true")

        serializer = ProductoListSerializer(productos, many=True)

        return Response(
            {
                "categoria": categoria.nombre,
                "total_productos": productos.count(),
                "productos": serializer.data,
            }
        )

    @action(
        detail=True, methods=["get"], permission_classes=[IsAuthenticated, EsSupervisor]
    )
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas de una categoría

        GET /api/categorias/{id}/estadisticas/

        Solo Supervisor o Admin
        """
        try:
            estadisticas = CategoriaService.obtener_estadisticas_categoria(pk)
            return Response(estadisticas)
        except Categoria.DoesNotExist:
            return Response(
                {"error": "Categoría no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
