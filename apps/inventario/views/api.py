# apps/inventario/views/api.py
"""
ViewSets para la API de Inventario

Este archivo contiene los ViewSets para:
- Inventario (stock)
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

from apps.inventario.models import Inventario, MovimientoInventario

from apps.inventario.serializers import (
    InventarioReadSerializer,
    MovimientoInventarioReadSerializer,
    MovimientoInventarioCreateSerializer,
)

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
