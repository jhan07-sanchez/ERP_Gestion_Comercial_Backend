# apps/compras/views/api.py
"""
🔹 VIEWSETS MEJORADOS - Versión 2.0
====================================

Características:
- Paginación automática
- Filtros avanzados
- Ordenamiento flexible
- Búsqueda optimizada
- Mejor manejo de errores
- Response consistentes

Autor: Sistema ERP
Versión: 2.0
Fecha: 2026-02-15
"""

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Sum
from django_filters.rest_framework import DjangoFilterBackend
import logging
from apps.auditorias.mixins import MixinAuditable
from apps.auditorias.services.auditoria_service import AuditoriaService
from apps.auditorias.utils import snapshot_objeto

from apps.compras.models import Compra, DetalleCompra
from apps.compras.serializers import (
    # Read
    CompraListSerializer,
    CompraDetailSerializer,
    DetalleCompraReadSerializer,
    # Write
    CompraCreateSerializer,
    CompraUpdateSerializer,
    CompraAnularSerializer,
)
from apps.compras.services import (
    CompraService,
    CompraError,
    CompraStateError,
    InventarioInsuficienteError,
)
from apps.usuarios.permissions import (
    EsSupervisor,
    EsAlmacenista,
    PuedeGestionarCompras,
)

logger = logging.getLogger("compras")


# ============================================================================
# PAGINACIÓN PERSONALIZADA
# ============================================================================


class CompraPagination(PageNumberPagination):
    """
    Paginación para compras

    - 20 items por página (default)
    - Cliente puede ajustar hasta 100
    - Incluye metadata útil
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        """Response con metadata extendida"""
        return Response(
            {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.page_size,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            }
        )


# ============================================================================
# VIEWSET DE COMPRAS
# ============================================================================


class CompraViewSet(MixinAuditable, viewsets.ModelViewSet):
    """
    ViewSet completo para gestión de compras

    Endpoints:
    - list: GET /api/compras/
    - create: POST /api/compras/
    - retrieve: GET /api/compras/{id}/
    - update: PUT /api/compras/{id}/
    - partial_update: PATCH /api/compras/{id}/
    - destroy: DELETE /api/compras/{id}/
    - confirmar: POST /api/compras/{id}/confirmar/
    - anular: POST /api/compras/{id}/anular/
    - estadisticas: GET /api/compras/{id}/estadisticas/
    - resumen: GET /api/compras/resumen/

    Filtros disponibles:
    - proveedor_id: Filtrar por proveedor
    - estado: Filtrar por estado (PENDIENTE, REALIZADA, ANULADA)
    - fecha_inicio, fecha_fin: Rango de fechas
    - search: Búsqueda por número de compra, proveedor
    - ordering: Ordenar por cualquier campo

    Permisos:
    - Listar/Ver: Almacenista o superior
    - Crear/Actualizar: Puede gestionar compras
    - Confirmar/Anular: Supervisor o superior
    """

    queryset = Compra.objects.select_related("proveedor", "usuario").prefetch_related(
        "detalles__producto"
    )

    pagination_class = CompraPagination

    # Filtros y búsqueda
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = ["proveedor", "estado", "usuario"]
    search_fields = ["numero_compra", "proveedor__nombre"]
    ordering_fields = ["fecha", "total", "numero_compra", "estado"]
    ordering = ["-fecha"]  # Por defecto, más recientes primero

    def get_serializer_class(self):
        """Seleccionar serializer según la acción"""
        if self.action == "list":
            return CompraListSerializer
        elif self.action == "create":
            return CompraCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return CompraUpdateSerializer
        elif self.action == "anular":
            return CompraAnularSerializer
        return CompraDetailSerializer

    modulo_auditoria = 'COMPRAS'

    def create(self, request, *args, **kwargs):
        """Crear compra usando el servicio"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            compra = CompraService.crear_compra(
                proveedor_id=serializer.validated_data['proveedor_id'],
                detalles=serializer.validated_data['detalles'],
                usuario=request.user,
                estado=serializer.validated_data.get('estado', 'PENDIENTE')
            )

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='CREAR',
                modulo=self.modulo_auditoria,
                objeto=compra,
                descripcion=f"Compra creada: ID {compra.id} - Proveedor: {compra.proveedor.nombre}",
                request=request,
                datos_despues=snapshot_objeto(compra)
            )

            response_serializer = CompraDetailSerializer(compra)
            return Response(
                {
                    'detail': 'Compra creada exitosamente',
                    'compra': response_serializer.data
                },
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get_permissions(self):
        """Permisos según la acción"""
        if self.action in ["list", "retrieve"]:
            permission_classes = [IsAuthenticated, EsAlmacenista]
        elif self.action in ["create", "update", "partial_update"]:
            permission_classes = [IsAuthenticated, PuedeGestionarCompras]
        elif self.action in ["destroy", "confirmar", "anular"]:
            permission_classes = [IsAuthenticated, EsSupervisor]
        else:
            permission_classes = [IsAuthenticated]

        return [permission() for permission in permission_classes]

    def get_queryset(self):
        """
        Filtrar compras con filtros avanzados

        Soporta:
        - Rango de fechas
        - Rango de totales
        - Múltiples estados
        """
        queryset = super().get_queryset()

        # Filtro por rango de fechas
        fecha_inicio = self.request.query_params.get("fecha_inicio")
        fecha_fin = self.request.query_params.get("fecha_fin")

        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        # Filtro por rango de total
        total_min = self.request.query_params.get("total_min")
        total_max = self.request.query_params.get("total_max")

        if total_min:
            queryset = queryset.filter(total__gte=total_min)
        if total_max:
            queryset = queryset.filter(total__lte=total_max)

        return queryset

    # ========================================================================
    # CREAR COMPRA
    # ========================================================================

    def create(self, request, *args, **kwargs):
        """
        Crear nueva compra

        POST /api/compras/
        Body: {
            "proveedor_id": 1,
            "fecha": "2026-02-15",
            "observaciones": "...",
            "detalles": [
                {"producto_id": 1, "cantidad": 10, "precio_compra": 1000}
            ]
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            compra = CompraService.crear_compra(
                proveedor=serializer.validated_data["proveedor"],
                detalles=serializer.validated_data["detalles"],
                usuario=request.user,
                fecha=serializer.validated_data["fecha"],
                observaciones=serializer.validated_data.get("observaciones"),
            )

            response_serializer = CompraDetailSerializer(compra)

            return Response(
                {
                    "success": True,
                    "message": "Compra creada exitosamente",
                    "data": response_serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except CompraError as e:
            logger.warning(f"Error al crear compra: {str(e)}")
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error inesperado al crear compra: {str(e)}")
            return Response(
                {"success": False, "error": "Error interno del servidor"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # ========================================================================
    # ACTUALIZAR COMPRA
    # ========================================================================

    def update(self, request, *args, **kwargs):
        """
        Actualizar compra existente

        PUT/PATCH /api/compras/{id}/
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        try:
            serializer.save()
            response_serializer = CompraDetailSerializer(instance)

            return Response(
                {
                    "success": True,
                    "message": "Compra actualizada exitosamente",
                    "data": response_serializer.data,
                }
            )

        except CompraError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ========================================================================
    # CONFIRMAR COMPRA
    # ========================================================================

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """
        Confirmar compra (marcar como REALIZADA y actualizar inventario)

        POST /api/compras/{id}/confirmar/
        """
        try:
            compra = CompraService.confirmar_compra(compra_id=pk, usuario=request.user)

            serializer = CompraDetailSerializer(compra)

            return Response(
                {
                    "success": True,
                    "message": f"Compra {compra.numero_compra} confirmada exitosamente",
                    "data": serializer.data,
                }
            )

        except CompraStateError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except CompraError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ========================================================================
    # ANULAR COMPRA
    # ========================================================================

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        """
        Anular una compra

        POST /api/compras/{id}/anular/
        Body: {"motivo": "Motivo de la anulación"}
        """
        serializer = CompraAnularSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            compra = CompraService.anular_compra(
                compra_id=pk,
                usuario=request.user,
                motivo=serializer.validated_data["motivo"],
            )

            response_serializer = CompraDetailSerializer(compra)

            return Response(
                {
                    "success": True,
                    "message": f"Compra {compra.numero_compra} anulada exitosamente",
                    "data": response_serializer.data,
                }
            )

        except CompraStateError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except InventarioInsuficienteError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except CompraError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ========================================================================
    # ELIMINAR COMPRA
    # ========================================================================

    def destroy(self, request, *args, **kwargs):
        """
        Eliminar compra (internamente la anula)

        DELETE /api/compras/{id}/
        """
        instance = self.get_object()

        try:
            CompraService.anular_compra(
                compra_id=instance.id,
                usuario=request.user,
                motivo="Eliminación directa por el usuario",
            )

            return Response(
                {"success": True, "message": "Compra eliminada exitosamente"},
                status=status.HTTP_200_OK,
            )

        except CompraError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================

    @action(detail=True, methods=["get"])
    def estadisticas(self, request, pk=None):
        """
        Obtener estadísticas de una compra

        GET /api/compras/{id}/estadisticas/
        """
        try:
            estadisticas = CompraService.obtener_estadisticas_compra(pk)
            return Response({"success": True, "data": estadisticas})
        except CompraError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """
        Obtener resumen general de compras

        GET /api/compras/resumen/?fecha_inicio=2026-01-01&fecha_fin=2026-12-31
        """
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        try:
            estadisticas = CompraService.obtener_estadisticas_generales(
                fecha_inicio=fecha_inicio, fecha_fin=fecha_fin
            )
            return Response({"success": True, "data": estadisticas})
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# VIEWSET DE DETALLES (Solo lectura)
# ============================================================================


class DetalleCompraViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar detalles de compra (Solo lectura)

    Los detalles se crean automáticamente con la compra
    """

    queryset = DetalleCompra.objects.select_related("compra", "producto")
    serializer_class = DetalleCompraReadSerializer
    permission_classes = [IsAuthenticated, EsAlmacenista]
    pagination_class = CompraPagination

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["compra", "producto"]
    ordering_fields = ["id", "cantidad", "precio_compra"]
    ordering = ["id"]
