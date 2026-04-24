from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from django.db.models import Q

from apps.auditorias.mixins import MixinAuditable
from apps.auditorias.services.auditoria_service import AuditoriaService
from apps.auditorias.utils import snapshot_objeto

from apps.precios.models import ListaPrecioCompra
from apps.precios.services.precio_service import ListaPrecioCompraService

from apps.precios.serializers.read import (
    ListaPrecioCompraListSerializer,
    ListaPrecioCompraDetailSerializer,
    ListaPrecioCompraSimpleSerializer,
)

from apps.precios.serializers.write import (
    ListaPrecioCompraCreateSerializer,
    ListaPrecioCompraUpdateSerializer,
)


class ListaPrecioCompraViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet profesional para Lista de Precios de Compra
    """

    # 🔥 IMPORTANTE: .all() para evitar bugs internos de DRF
    queryset = ListaPrecioCompra.objects.select_related("producto", "proveedor").all()

    permission_classes = [IsAuthenticated]
    modulo_auditoria = "PRECIOS"

    # =========================================================
    # SERIALIZERS DINÁMICOS
    # =========================================================
    def get_serializer_class(self):
        if self.action == "create":
            return ListaPrecioCompraCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return ListaPrecioCompraUpdateSerializer
        elif self.action == "retrieve":
            return ListaPrecioCompraDetailSerializer
        return ListaPrecioCompraListSerializer

    # =========================================================
    # FILTROS
    # =========================================================
    def get_queryset(self):
        queryset = super().get_queryset()

        producto = self.request.query_params.get("producto")
        proveedor = self.request.query_params.get("proveedor")
        vigente = self.request.query_params.get("vigente")
        search = self.request.query_params.get("search")

        if producto:
            queryset = queryset.filter(producto_id=producto)

        if proveedor:
            queryset = queryset.filter(proveedor_id=proveedor)

        if vigente is not None:
            queryset = queryset.filter(vigente=vigente.lower() == "true")

        if search:
            queryset = queryset.filter(
                Q(producto__nombre__icontains=search)
                | Q(proveedor__nombre__icontains=search)
            )

        return queryset.order_by("-fecha_inicio")

    # =========================================================
    # CREATE
    # =========================================================
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            precio = ListaPrecioCompraService.crear_precio(
                producto=serializer.validated_data["producto"],
                proveedor=serializer.validated_data["proveedor"],
                precio=serializer.validated_data["precio"],
                fecha_inicio=serializer.validated_data.get("fecha_inicio"),
                usuario=request.user,
            )

            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion="CREAR",
                modulo=self.modulo_auditoria,
                objeto=precio,
                descripcion=f"Nuevo precio: {precio.producto.nombre} / {precio.proveedor.nombre} (${precio.precio})",
                request=request,
                datos_despues=snapshot_objeto(precio),
            )

            return Response(
                ListaPrecioCompraDetailSerializer(precio).data,
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # =========================================================
    # UPDATE
    # =========================================================
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        datos_antes = snapshot_objeto(instance)

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.get("partial", False),
        )
        serializer.is_valid(raise_exception=True)

        try:
            precio = ListaPrecioCompraService.actualizar_precio(
                precio_id=instance.id,
                precio=serializer.validated_data.get("precio"),
                fecha_inicio=serializer.validated_data.get("fecha_inicio"),
                fecha_fin=serializer.validated_data.get("fecha_fin"),
            )

            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion="ACTUALIZAR",
                modulo=self.modulo_auditoria,
                objeto=precio,
                descripcion=f"Precio actualizado ID {precio.id}",
                request=request,
                datos_antes=datos_antes,
                datos_despues=snapshot_objeto(precio),
            )

            return Response(ListaPrecioCompraDetailSerializer(precio).data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # =========================================================
    # DELETE → DESACTIVAR
    # =========================================================
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        try:
            ListaPrecioCompraService.desactivar_precio(instance.id)

            return Response(
                {"detail": "Precio desactivado correctamente."},
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # =========================================================
    # PRECIO VIGENTE
    # =========================================================
    @action(detail=False, methods=["get"])
    def precio_vigente(self, request):
        producto_id = request.query_params.get("producto")
        proveedor_id = request.query_params.get("proveedor")

        if not producto_id or not proveedor_id:
            return Response(
                {"error": "producto y proveedor son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        precio = ListaPrecioCompraService.obtener_precio_vigente(
            producto_id, proveedor_id
        )

        if not precio:
            return Response({"precio": None})

        return Response(ListaPrecioCompraSimpleSerializer(precio).data)

    # =========================================================
    # HISTORIAL
    # =========================================================
    @action(detail=False, methods=["get"])
    def historial(self, request):
        producto_id = request.query_params.get("producto")
        proveedor_id = request.query_params.get("proveedor")

        if not producto_id or not proveedor_id:
            return Response(
                {"error": "producto y proveedor son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = ListaPrecioCompraService.obtener_historial(producto_id, proveedor_id)

        serializer = ListaPrecioCompraListSerializer(queryset, many=True)
        return Response(serializer.data)

    # =========================================================
    # ESTADÍSTICAS
    # =========================================================
    @action(detail=False, methods=["get"])
    def estadisticas(self, request):
        producto_id = request.query_params.get("producto")

        if not producto_id:
            return Response(
                {"error": "producto es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = ListaPrecioCompraService.obtener_estadisticas_producto(producto_id)
            return Response(data)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    # =========================================================
    # COMPARAR PROVEEDORES
    # =========================================================
    @action(detail=False, methods=["get"])
    def comparar(self, request):
        producto_id = request.query_params.get("producto")

        if not producto_id:
            return Response(
                {"error": "producto es requerido"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = ListaPrecioCompraService.comparar_proveedores(producto_id)
        serializer = ListaPrecioCompraListSerializer(queryset, many=True)

        return Response(serializer.data)
