# apps/productos/views/api.py
"""
ViewSets para la API de Productos

Los ViewSets utilizan:
- Serializers (read y write)
- Services (lógica de negocio)
- Permissions (control de acceso)
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, F
from apps.auditorias.mixins import MixinAuditable

from apps.productos.models import Producto

from apps.productos.serializers import (
    ProductoListSerializer,
    ProductoDetailSerializer,
    ProductoCreateSerializer,
    ProductoUpdateSerializer,
    AjusteInventarioSerializer,
)

from apps.inventario.serializers import (
    MovimientoInventarioReadSerializer,
)

from apps.productos.services import ProductoService

from apps.inventario.services import (
    InventarioService,
    MovimientoInventarioService,
)

from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsAlmacenista,
    PuedeGestionarInventario,
    PuedeEliminar,
)


# ============================================================================
# VIEWSET DE PRODUCTOS
# ============================================================================


class ProductoViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet para gestionar productos
    """
    modulo_auditoria = "INVENTARIO"
    """
    ViewSet para gestionar productos

    Endpoints:
    - list: GET /api/productos/
    - create: POST /api/productos/
    - retrieve: GET /api/productos/{id}/
    - update: PUT /api/productos/{id}/
    - partial_update: PATCH /api/productos/{id}/
    - destroy: DELETE /api/productos/{id}/
    - stock_bajo: GET /api/productos/stock_bajo/
    - activar: POST /api/productos/{id}/activar/
    - desactivar: POST /api/productos/{id}/desactivar/
    - movimientos: GET /api/productos/{id}/movimientos/
    - estadisticas: GET /api/productos/{id}/estadisticas/
    - ajustar_stock: POST /api/productos/{id}/ajustar_stock/

    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear/Editar: Almacenista o superior
    - Eliminar: Solo Supervisor o Admin
    - Acciones especiales: Supervisor o Admin
    """

    queryset = Producto.objects.select_related("categoria").prefetch_related(
        "inventario"
    )

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == "list":
            return ProductoListSerializer
        elif self.action == "create":
            return ProductoCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ProductoUpdateSerializer
        elif self.action == "ajustar_stock":
            return AjusteInventarioSerializer
        return ProductoDetailSerializer

    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated, EsAlmacenista]

        elif self.action in ["create", "update", "partial_update"]:
            permission_classes = [IsAuthenticated, PuedeGestionarInventario]

        elif self.action == "destroy":
            permission_classes = [IsAuthenticated, PuedeEliminar]

        elif self.action in [
            "activar",
            "desactivar",
            "stock_bajo",
            "estadisticas",
            "ajustar_stock",
        ]:
            permission_classes = [IsAuthenticated, EsSupervisor]

        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """Filtrar productos según parámetros"""
        queryset = Producto.objects.select_related("categoria")

        # Filtro por categoría
        categoria_id = self.request.query_params.get("categoria_id", None)
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        # Filtro por nombre de categoría

        categoria_nombre = self.request.query_params.get("categoria", None)
        if categoria_nombre:
            queryset = queryset.filter(categoria__nombre__icontains=categoria_nombre)
        # Filtro por nombre de categoría

        # Filtro por estado
        estado = self.request.query_params.get("estado", None)
        if estado is not None:
            queryset = queryset.filter(estado=estado.lower() == "true")

        # Filtro por rango de precio
        precio_min = self.request.query_params.get("precio_min", None)
        precio_max = self.request.query_params.get("precio_max", None)

        if precio_min:
            queryset = queryset.filter(precio_venta__gte=precio_min)
        if precio_max:
            queryset = queryset.filter(precio_venta__lte=precio_max)

        # Búsqueda general
        search = self.request.query_params.get("search", None)
        if search:
            queryset = queryset.filter(
                Q(nombre__icontains=search)
                | Q(codigo__icontains=search)
                | Q(descripcion__icontains=search)
            )

        return queryset.order_by("-fecha_creacion")

    def create(self, request, *args, **kwargs):
        """Crear producto usando el servicio"""
        # Nota: MixinAuditable intercepta perform_create
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        """Actualizar producto usando el servicio"""
        # Nota: MixinAuditable intercepta perform_update
        return super().update(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Sobrescribimos para usar el servicio pero mantener auditoría"""
        producto = ProductoService.crear_producto(**serializer.validated_data)
        # Sincronizamos el serializer con el objeto creado
        serializer.instance = producto
        # Llamamos al super para que el Mixin haga el log
        super().perform_create(serializer)

    def perform_update(self, serializer):
        """Sobrescribimos para usar el servicio pero mantener auditoría"""
        producto = ProductoService.actualizar_producto(
            producto_id=self.get_object().id, **serializer.validated_data
        )
        # Sincronizamos el serializer
        serializer.instance = producto
        # Llamamos al super para que el Mixin haga el log
        super().perform_update(serializer)

    @action(detail=False, methods=["get"])
    def stock_bajo(self, request):
        """
        Obtener productos con stock bajo

        GET /api/productos/stock_bajo/
        """
        productos = ProductoService.obtener_productos_stock_bajo()
        serializer = ProductoListSerializer(productos, many=True)

        return Response({"count": productos.count(), "productos": serializer.data})

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """
        Activar un producto

        POST /api/productos/{id}/activar/
        """
        try:
            producto = ProductoService.activar_producto(pk)
            return Response(
                {
                    "detail": f"Producto {producto.nombre} activado exitosamente",
                    "producto": ProductoDetailSerializer(producto).data,
                }
            )
        except Producto.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """
        Desactivar un producto

        POST /api/productos/{id}/desactivar/
        """
        try:
            producto = ProductoService.desactivar_producto(pk)
            return Response(
                {
                    "detail": f"Producto {producto.nombre} desactivado exitosamente",
                    "producto": ProductoDetailSerializer(producto).data,
                }
            )
        except Producto.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["get"])
    def movimientos(self, request, pk=None):
        """
        Obtener historial de movimientos de un producto

        GET /api/productos/{id}/movimientos/
        """
        producto = self.get_object()
        movimientos = producto.movimientos.select_related("usuario").order_by("-fecha")

        # Filtros
        tipo = request.query_params.get("tipo", None)
        if tipo:
            movimientos = movimientos.filter(tipo_movimiento=tipo.upper())

        fecha_inicio = request.query_params.get("fecha_inicio", None)
        fecha_fin = request.query_params.get("fecha_fin", None)

        if fecha_inicio:
            movimientos = movimientos.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            movimientos = movimientos.filter(fecha__lte=fecha_fin)

        serializer = MovimientoInventarioReadSerializer(movimientos, many=True)

        return Response(
            {
                "producto": producto.nombre,
                "total_movimientos": movimientos.count(),
                "movimientos": serializer.data,
            }
        )

    @action(detail=True, methods=["get"])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas del producto

        GET /api/productos/{id}/estadisticas/
        """
        try:
            estadisticas = ProductoService.obtener_estadisticas_producto(pk)
            return Response(estadisticas)
        except Producto.DoesNotExist:
            return Response(
                {"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=True, methods=["post"])
    def ajustar_stock(self, request, pk=None):
        """
        Ajustar el stock manualmente

        POST /api/productos/{id}/ajustar_stock/
        Body: {
            "stock_nuevo": 100,
            "motivo": "Ajuste por inventario físico"
        }
        """
        producto = self.get_object()
        serializer = AjusteInventarioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            inventario, movimiento = InventarioService.ajustar_stock(
                producto_id=producto.id,
                stock_nuevo=serializer.validated_data["stock_nuevo"],
                usuario=request.user,
                motivo=serializer.validated_data["motivo"],
            )

            return Response(
                {
                    "detail": "Stock ajustado exitosamente",
                    "stock_anterior": movimiento.cantidad
                    if movimiento.tipo_movimiento == "SALIDA"
                    else 0,
                    "stock_nuevo": inventario.stock_actual,
                    "movimiento": MovimientoInventarioReadSerializer(movimiento).data,
                }
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def siguiente_codigo(self, request):
        """
        Obtener el siguiente código disponible para producto

        GET /api/productos/siguiente_codigo/
        """
        codigo = Producto.generar_siguiente_codigo()
        return Response({"codigo": codigo})
