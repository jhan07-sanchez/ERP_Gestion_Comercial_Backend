# apps/inventario/views/api.py
"""
ViewSets para la API de Inventario

Este archivo contiene los ViewSets para:
- Productos
- Categorías
- Inventario
- Movimientos de Inventario

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

from apps.inventario.models import Producto, Categoria, Inventario, MovimientoInventario

from apps.inventario.serializers import (
    # Read
    CategoriaReadSerializer,
    ProductoListSerializer,
    ProductoDetailSerializer,
    InventarioReadSerializer,
    MovimientoInventarioReadSerializer,
    # Write
    CategoriaWriteSerializer,
    ProductoCreateSerializer,
    ProductoUpdateSerializer,
    MovimientoInventarioCreateSerializer,
    AjusteInventarioSerializer,
)

from apps.inventario.services import (
    CategoriaService,
    ProductoService,
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
# VIEWSET DE CATEGORÍAS
# ============================================================================


class CategoriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de productos

    Endpoints:
    - list: GET /api/inventario/categorias/
    - create: POST /api/inventario/categorias/
    - retrieve: GET /api/inventario/categorias/{id}/
    - update: PUT /api/inventario/categorias/{id}/
    - partial_update: PATCH /api/inventario/categorias/{id}/
    - destroy: DELETE /api/inventario/categorias/{id}/
    - productos: GET /api/inventario/categorias/{id}/productos/
    - estadisticas: GET /api/inventario/categorias/{id}/estadisticas/

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

        GET /api/inventario/categorias/{id}/productos/
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

        GET /api/inventario/categorias/{id}/estadisticas/

        Solo Supervisor o Admin
        """
        try:
            estadisticas = CategoriaService.obtener_estadisticas_categoria(pk)
            return Response(estadisticas)
        except Categoria.DoesNotExist:
            return Response(
                {"error": "Categoría no encontrada."}, status=status.HTTP_404_NOT_FOUND
            )


# ============================================================================
# VIEWSET DE PRODUCTOS
# ============================================================================


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar productos

    Endpoints:
    - list: GET /api/inventario/productos/
    - create: POST /api/inventario/productos/
    - retrieve: GET /api/inventario/productos/{id}/
    - update: PUT /api/inventario/productos/{id}/
    - partial_update: PATCH /api/inventario/productos/{id}/
    - destroy: DELETE /api/inventario/productos/{id}/
    - stock_bajo: GET /api/inventario/productos/stock_bajo/
    - activar: POST /api/inventario/productos/{id}/activar/
    - desactivar: POST /api/inventario/productos/{id}/desactivar/
    - movimientos: GET /api/inventario/productos/{id}/movimientos/
    - estadisticas: GET /api/inventario/productos/{id}/estadisticas/
    - ajustar_stock: POST /api/inventario/productos/{id}/ajustar_stock/

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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            producto = ProductoService.crear_producto(**serializer.validated_data)

            response_serializer = ProductoDetailSerializer(producto)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        """Actualizar producto usando el servicio"""
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            producto = ProductoService.actualizar_producto(
                producto_id=instance.id, **serializer.validated_data
            )

            response_serializer = ProductoDetailSerializer(producto)
            return Response(response_serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    
    @action(detail=False, methods=["get"])
    def stock_bajo(self, request):
        """
        Obtener productos con stock bajo

        GET /api/inventario/productos/stock_bajo/
        """
        productos = ProductoService.obtener_productos_stock_bajo()
        serializer = ProductoListSerializer(productos, many=True)

        return Response({"count": productos.count(), "productos": serializer.data})

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """
        Activar un producto

        POST /api/inventario/productos/{id}/activar/
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

        POST /api/inventario/productos/{id}/desactivar/
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

        GET /api/inventario/productos/{id}/movimientos/
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

        GET /api/inventario/productos/{id}/estadisticas/
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

        POST /api/inventario/productos/{id}/ajustar_stock/
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

        GET /api/inventario/productos/siguiente_codigo/
        """
        codigo = Producto.generar_siguiente_codigo()
        return Response({"codigo": codigo})

# ============================================================================
# VIEWSET DE INVENTARIO
# ============================================================================


class InventarioViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar inventario (Solo lectura)

    Endpoints:
    - list: GET /api/inventario/inventarios/
    - retrieve: GET /api/inventario/inventarios/{id}/
    - estadisticas: GET /api/inventario/inventarios/estadisticas/

    Permisos:
    - Ver: Almacenista o superior
    - Estadísticas: Supervisor o Admin

    Nota: El inventario se actualiza automáticamente con los movimientos,
    no se edita directamente.
    """

    queryset = Inventario.objects.select_related("producto")
    serializer_class = InventarioReadSerializer
    permission_classes = [IsAuthenticated, EsAlmacenista]

    def get_queryset(self):
        """Filtrar inventario según parámetros"""
        queryset = Inventario.objects.select_related("producto", "producto__categoria")

        # Filtro por stock bajo
        stock_bajo = self.request.query_params.get("stock_bajo", None)
        if stock_bajo and stock_bajo.lower() == "true":
            queryset = queryset.filter(stock_actual__lte=F("producto__stock_minimo"))

        # Filtro por categoría
        categoria = self.request.query_params.get("categoria", None)
        if categoria:
            queryset = queryset.filter(producto__categoria__nombre__icontains=categoria)

        # Filtro por productos activos
        solo_activos = self.request.query_params.get("solo_activos", None)
        if solo_activos and solo_activos.lower() == "true":
            queryset = queryset.filter(producto__estado=True)

        return queryset.order_by("-fecha_actualizacion")

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated, EsSupervisor],
    )
    def estadisticas(self, request):
        """
        Obtener estadísticas generales del inventario

        GET /api/inventario/inventarios/estadisticas/

        Solo Supervisor o Admin
        """
        try:
            estadisticas = InventarioService.obtener_estadisticas_generales()
            return Response(estadisticas)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ============================================================================
# VIEWSET DE MOVIMIENTOS DE INVENTARIO
# ============================================================================


class MovimientoInventarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar movimientos de inventario

    Endpoints:
    - list: GET /api/inventario/movimientos/
    - create: POST /api/inventario/movimientos/
    - retrieve: GET /api/inventario/movimientos/{id}/
    - resumen: GET /api/inventario/movimientos/resumen/

    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear: Almacenista o superior
    - Editar/Eliminar: No permitido (inmutables)

    Nota: Los movimientos de inventario NO se pueden editar o eliminar
    una vez creados para mantener el historial intacto.
    """

    queryset = MovimientoInventario.objects.select_related("producto", "usuario")
    serializer_class = MovimientoInventarioReadSerializer
    permission_classes = [IsAuthenticated, PuedeGestionarInventario]
    http_method_names = ["get", "post", "head", "options"]  # Solo GET y POST

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == "create":
            return MovimientoInventarioCreateSerializer
        return MovimientoInventarioReadSerializer

    def get_queryset(self):
        """Filtrar movimientos según parámetros"""
        queryset = MovimientoInventario.objects.select_related("producto", "usuario")

        # Filtro por producto
        producto_id = self.request.query_params.get("producto_id", None)
        if producto_id:
            queryset = queryset.filter(producto_id=producto_id)

        # Filtro por tipo de movimiento
        tipo = self.request.query_params.get("tipo", None)
        if tipo:
            queryset = queryset.filter(tipo_movimiento=tipo.upper())

        # Filtro por referencia
        referencia = self.request.query_params.get("referencia", None)
        if referencia:
            queryset = queryset.filter(referencia__icontains=referencia)

        # Filtro por usuario
        usuario_id = self.request.query_params.get("usuario_id", None)
        if usuario_id:
            queryset = queryset.filter(usuario_id=usuario_id)

        # Filtro por fecha
        fecha_inicio = self.request.query_params.get("fecha_inicio", None)
        fecha_fin = self.request.query_params.get("fecha_fin", None)

        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        return queryset.order_by("-fecha")

    def create(self, request, *args, **kwargs):
        """Crear movimiento usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tipo = serializer.validated_data["tipo_movimiento"]
        producto_id = serializer.validated_data["producto"].id
        cantidad = serializer.validated_data["cantidad"]
        referencia = serializer.validated_data["referencia"]

        try:
            if tipo == "ENTRADA":
                movimiento, inventario = MovimientoInventarioService.registrar_entrada(
                    producto_id=producto_id,
                    cantidad=cantidad,
                    referencia=referencia,
                    usuario=request.user,
                )
            else:  # SALIDA
                movimiento, inventario = MovimientoInventarioService.registrar_salida(
                    producto_id=producto_id,
                    cantidad=cantidad,
                    referencia=referencia,
                    usuario=request.user,
                )

            response_serializer = MovimientoInventarioReadSerializer(movimiento)
            return Response(
                {
                    "detail": "Movimiento registrado exitosamente",
                    "movimiento": response_serializer.data,
                    "stock_actual": inventario.stock_actual,
                },
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["get"],
        permission_classes=[IsAuthenticated, EsSupervisor],
    )
    def resumen(self, request):
        """
        Obtener resumen de movimientos

        GET /api/inventario/movimientos/resumen/

        Query params:
        - fecha_inicio: Fecha inicial (YYYY-MM-DD)
        - fecha_fin: Fecha final (YYYY-MM-DD)

        Solo Supervisor o Admin
        """
        fecha_inicio = request.query_params.get("fecha_inicio", None)
        fecha_fin = request.query_params.get("fecha_fin", None)

        try:
            resumen = MovimientoInventarioService.obtener_resumen_movimientos(
                fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
            )
            return Response(resumen)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
