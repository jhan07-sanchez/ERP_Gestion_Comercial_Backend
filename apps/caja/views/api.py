# apps/caja/views/api.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      API VIEWS - MÓDULO CAJA                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

📚 ¿Qué hace este archivo?

Contiene los ViewSets que manejan las peticiones HTTP.
Cada ViewSet es responsable de:
1. Recibir la petición (GET, POST, etc.)
2. Validar los datos con el serializer
3. Llamar al service o selector correspondiente
4. Devolver la respuesta

Los ViewSets NO tienen lógica de negocio — esa está en services/.
Los ViewSets NO tienen consultas complejas — esas están en selectors/.
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from apps.caja.models import Caja, SesionCaja, MovimientoCaja, MetodoPago
from apps.caja.services import (
    CajaService,
    MetodoPagoService,
    CajaError,
    CajaYaAbiertaError,
    CajaCerradaError,
    SesionNoEncontradaError,
    MovimientoInvalidoError,
)
from apps.caja.selectors import (
    CajaSelector,
    MovimientoSelector,
    EstadisticasCajaSelector,
)
from apps.caja.serializers import (
    # READ
    MetodoPagoSerializer,
    CajaListSerializer,
    CajaDetailSerializer,
    SesionCajaListSerializer,
    SesionCajaDetailSerializer,
    MovimientoCajaListSerializer,
    MovimientoCajaDetailSerializer,
    ArqueoCajaReadSerializer,
    # WRITE
    MetodoPagoCreateSerializer,
    CajaCreateSerializer,
    CajaUpdateSerializer,
    AbrirCajaSerializer,
    CerrarCajaSerializer,
    MovimientoCajaCreateSerializer,
    ArqueoCajaWriteSerializer,
)
from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsCajero,
)

logger = logging.getLogger("caja")


# ============================================================================
# VIEWSET - MÉTODOS DE PAGO
# ============================================================================


class MetodoPagoViewSet(viewsets.ModelViewSet):
    """
    CRUD de métodos de pago.

    Endpoints:
      GET    /api/caja/metodos-pago/          - Listar todos
      POST   /api/caja/metodos-pago/          - Crear nuevo
      GET    /api/caja/metodos-pago/{id}/     - Ver detalle
      PATCH  /api/caja/metodos-pago/{id}/     - Actualizar
      POST   /api/caja/metodos-pago/{id}/activar/   - Activar
      POST   /api/caja/metodos-pago/{id}/desactivar/ - Desactivar
    """

    queryset = MetodoPago.objects.all()

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return MetodoPagoCreateSerializer
        return MetodoPagoSerializer

    def get_permissions(self):
        if self.action in [
            "create",
            "update",
            "partial_update",
            "destroy",
            "activar",
            "desactivar",
        ]:
            permission_classes = [IsAuthenticated, EsAdministrador]
        else:
            permission_classes = [IsAuthenticated, EsCajero]
        return [p() for p in permission_classes]

    @action(detail=True, methods=["post"])
    def activar(self, request, pk=None):
        """POST /api/caja/metodos-pago/{id}/activar/"""
        try:
            metodo = MetodoPagoService.activar(pk)
            return Response(
                {
                    "success": True,
                    "message": f'Método "{metodo.nombre}" activado',
                    "data": MetodoPagoSerializer(metodo).data,
                }
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=["post"])
    def desactivar(self, request, pk=None):
        """POST /api/caja/metodos-pago/{id}/desactivar/"""
        try:
            metodo = MetodoPagoService.desactivar(pk)
            return Response(
                {
                    "success": True,
                    "message": f'Método "{metodo.nombre}" desactivado',
                    "data": MetodoPagoSerializer(metodo).data,
                }
            )
        except Exception as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# VIEWSET - CAJAS
# ============================================================================


class CajaViewSet(viewsets.ModelViewSet):
    """
    Gestión de cajas físicas.

    Endpoints:
      GET    /api/caja/cajas/                  - Listar cajas
      POST   /api/caja/cajas/                  - Crear caja
      GET    /api/caja/cajas/{id}/             - Ver detalle
      PATCH  /api/caja/cajas/{id}/             - Actualizar
      POST   /api/caja/cajas/{id}/abrir/       - Abrir sesión en esta caja
    """

    filter_backends = [filters.SearchFilter]
    search_fields = ["nombre", "descripcion"]

    def get_queryset(self):
        return CajaSelector.get_todas()

    def get_serializer_class(self):
        if self.action == "create":
            return CajaCreateSerializer
        if self.action in ["update", "partial_update"]:
            return CajaUpdateSerializer
        if self.action == "retrieve":
            return CajaDetailSerializer
        return CajaListSerializer

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated, EsAdministrador]
        else:
            permission_classes = [IsAuthenticated, EsCajero]
        return [p() for p in permission_classes]

    def create(self, request, *args, **kwargs):
        """Crear nueva caja"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            caja = Caja.objects.create(**serializer.validated_data)
            return Response(
                {
                    "success": True,
                    "message": f'Caja "{caja.nombre}" creada exitosamente',
                    "data": CajaDetailSerializer(caja).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except CajaError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# VIEWSET - SESIONES DE CAJA
# ============================================================================


class SesionCajaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta de sesiones de caja.
    Las sesiones se crean a través de /abrir/ y se cierran con /cerrar/.

    Endpoints:
      GET  /api/caja/sesiones/                     - Listar sesiones
      GET  /api/caja/sesiones/{id}/                - Ver detalle
      POST /api/caja/sesiones/mi-sesion/           - Ver sesión activa propia
      POST /api/caja/sesiones/abrir/               - Abrir nueva sesión
      POST /api/caja/sesiones/{id}/cerrar/         - Cerrar sesión
      POST /api/caja/sesiones/{id}/movimiento/     - Registrar movimiento manual
      POST /api/caja/sesiones/{id}/arqueo/         - Realizar arqueo
      GET  /api/caja/sesiones/{id}/resumen/        - Resumen de la sesión
      GET  /api/caja/sesiones/resumen-hoy/         - Resumen del día
      GET  /api/caja/sesiones/resumen-rango/       - Resumen por rango de fechas
    """

    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["estado", "caja", "usuario"]
    ordering_fields = ["fecha_apertura", "fecha_cierre", "monto_inicial"]
    ordering = ["-fecha_apertura"]

    def get_queryset(self):
        """
        Filtrar sesiones según rol:
        - Cajero: solo ve sus propias sesiones
        - Supervisor/Admin: ve todas
        """
        user = self.request.user
        es_supervisor = user.usuario_roles.filter(
            rol__nombre__in=["Supervisor", "Administrador"]
        ).exists()

        return CajaSelector.get_sesiones_filtradas(
            usuario=None if es_supervisor else user,
            caja_id=self.request.query_params.get("caja_id"),
            estado=self.request.query_params.get("estado"),
            fecha_inicio=self.request.query_params.get("fecha_inicio"),
            fecha_fin=self.request.query_params.get("fecha_fin"),
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SesionCajaDetailSerializer
        return SesionCajaListSerializer

    def get_permissions(self):
        return [IsAuthenticated(), EsCajero()]

    # ── Mi sesión activa ──────────────────────────────────────────────────────

    @action(detail=False, methods=["get"], url_path="mi-sesion")
    def mi_sesion(self, request):
        """
        GET /api/caja/sesiones/mi-sesion/

        Retorna la sesión activa del usuario autenticado.
        Si no tiene sesión, retorna null.

        📚 El frontend usa este endpoint al cargar para saber si el
        cajero tiene caja abierta o no.
        """
        sesion = CajaSelector.get_sesion_activa_usuario(request.user)

        if not sesion:
            return Response(
                {
                    "sesion_activa": False,
                    "data": None,
                }
            )

        return Response(
            {
                "sesion_activa": True,
                "data": SesionCajaDetailSerializer(sesion).data,
            }
        )

    # ── Apertura ──────────────────────────────────────────────────────────────

    @action(detail=False, methods=["post"])
    def abrir(self, request):
        """
        POST /api/caja/sesiones/abrir/

        Body:
        {
            "caja_id": 1,
            "monto_inicial": 50000,
            "observaciones": "Turno de mañana"
        }
        """
        serializer = AbrirCajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sesion = CajaService.abrir_caja(
                caja_id=serializer.validated_data["caja_id"],
                usuario=request.user,
                monto_inicial=serializer.validated_data["monto_inicial"],
                observaciones=serializer.validated_data.get("observaciones"),
            )
            return Response(
                {
                    "success": True,
                    "message": f'Caja "{sesion.caja.nombre}" abierta exitosamente',
                    "data": SesionCajaDetailSerializer(sesion).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except CajaYaAbiertaError as e:
            return Response(
                {"success": False, "error": str(e)},
                status=status.HTTP_409_CONFLICT,  # 409 = conflicto de estado
            )
        except CajaError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ── Cierre ────────────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        """
        POST /api/caja/sesiones/{id}/cerrar/

        Body:
        {
            "monto_contado": 178500,
            "detalle_billetes": {"100000": 1, "50000": 1, "20000": 1, "5000": 1, "1000": 3, "500": 1},
            "observaciones": "Cierre normal"
        }
        """
        serializer = CerrarCajaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            sesion = CajaService.cerrar_caja(
                sesion_id=pk,
                usuario=request.user,
                monto_contado=serializer.validated_data["monto_contado"],
                detalle_billetes=serializer.validated_data.get("detalle_billetes", {}),
                observaciones=serializer.validated_data.get("observaciones"),
            )
            return Response(
                {
                    "success": True,
                    "message": f"Caja cerrada. Diferencia: ${sesion.diferencia:,.0f}",
                    "data": SesionCajaDetailSerializer(sesion).data,
                }
            )
        except (CajaCerradaError, SesionNoEncontradaError) as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )
        except CajaError as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ── Movimiento manual ─────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def movimiento(self, request, pk=None):
        """
        POST /api/caja/sesiones/{id}/movimiento/

        Body:
        {
            "tipo": "EGRESO_GASTO",
            "monto": 15000,
            "descripcion": "Compra de papelería",
            "metodo_pago_id": 1
        }
        """
        serializer = MovimientoCajaCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            movimiento = CajaService.registrar_movimiento(
                sesion_id=pk,
                tipo=serializer.validated_data["tipo"],
                monto=serializer.validated_data["monto"],
                descripcion=serializer.validated_data["descripcion"],
                metodo_pago_id=serializer.validated_data["metodo_pago_id"],
                usuario=request.user,
            )
            return Response(
                {
                    "success": True,
                    "message": f"{movimiento.get_tipo_display()} de ${movimiento.monto:,.0f} registrado",
                    "data": MovimientoCajaDetailSerializer(movimiento).data,
                },
                status=status.HTTP_201_CREATED,
            )
        except (
            CajaCerradaError,
            MovimientoInvalidoError,
            SesionNoEncontradaError,
        ) as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ── Arqueo ────────────────────────────────────────────────────────────────

    @action(detail=True, methods=["post"])
    def arqueo(self, request, pk=None):
        """
        POST /api/caja/sesiones/{id}/arqueo/

        Body:
        {
            "monto_contado": 130000,
            "detalle_billetes": {"50000": 2, "20000": 1, "10000": 1},
            "observaciones": "Revisión de medio día"
        }
        """
        serializer = ArqueoCajaWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            arqueo = CajaService.realizar_arqueo(
                sesion_id=pk,
                monto_contado=serializer.validated_data["monto_contado"],
                usuario=request.user,
                tipo="PARCIAL",
                detalle_billetes=serializer.validated_data.get("detalle_billetes", {}),
                observaciones=serializer.validated_data.get("observaciones"),
            )
            signo = "+" if arqueo.diferencia >= 0 else ""
            return Response(
                {
                    "success": True,
                    "message": f"Arqueo realizado. Diferencia: {signo}${arqueo.diferencia:,.0f}",
                    "data": ArqueoCajaReadSerializer(arqueo).data,
                }
            )
        except (CajaCerradaError, SesionNoEncontradaError) as e:
            return Response(
                {"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST
            )

    # ── Resumen de sesión ─────────────────────────────────────────────────────

    @action(detail=True, methods=["get"])
    def resumen(self, request, pk=None):
        """
        GET /api/caja/sesiones/{id}/resumen/

        Devuelve un resumen completo de la sesión con:
        - Totales por tipo de movimiento
        - Ingresos por método de pago
        - Diferencia si está cerrada
        """
        try:
            resumen = CajaService.obtener_resumen_sesion(sesion_id=pk)
            return Response(resumen)
        except SesionNoEncontradaError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

    # ── Resumen del día ───────────────────────────────────────────────────────

    @action(
        detail=False,
        methods=["get"],
        url_path="resumen-hoy",
        permission_classes=[IsAuthenticated, EsSupervisor],
    )
    def resumen_hoy(self, request):
        """
        GET /api/caja/sesiones/resumen-hoy/
        Solo supervisores y admins.
        """
        return Response(EstadisticasCajaSelector.get_resumen_hoy())

    # ── Resumen por rango ─────────────────────────────────────────────────────

    @action(
        detail=False,
        methods=["get"],
        url_path="resumen-rango",
        permission_classes=[IsAuthenticated, EsSupervisor],
    )
    def resumen_rango(self, request):
        """
        GET /api/caja/sesiones/resumen-rango/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
        Solo supervisores y admins.
        """
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")

        if not fecha_inicio or not fecha_fin:
            return Response(
                {"error": "Se requieren los parámetros fecha_inicio y fecha_fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            EstadisticasCajaSelector.get_resumen_rango(fecha_inicio, fecha_fin)
        )


# ============================================================================
# VIEWSET - MOVIMIENTOS (Solo lectura)
# ============================================================================


class MovimientoCajaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Consulta de movimientos de caja (solo lectura).
    Los movimientos se crean a través de las acciones de sesión.

    Endpoints:
      GET /api/caja/movimientos/          - Listar movimientos
      GET /api/caja/movimientos/{id}/     - Ver detalle

    Filtros:
      ?sesion_id=1        - Por sesión
      ?tipo=EGRESO_GASTO  - Por tipo
      ?fecha_inicio=...   - Por rango de fecha
    """

    filter_backends = [
        DjangoFilterBackend,
        filters.OrderingFilter,
        filters.SearchFilter,
    ]
    filterset_fields = ["tipo", "sesion", "metodo_pago"]
    ordering_fields = ["fecha", "monto"]
    ordering = ["-fecha"]
    search_fields = ["descripcion"]

    def get_queryset(self):
        user = self.request.user
        es_supervisor = user.usuario_roles.filter(
            rol__nombre__in=["Supervisor", "Administrador"]
        ).exists()

        sesion_id = self.request.query_params.get("sesion_id")
        tipo = self.request.query_params.get("tipo")
        metodo_pago_id = self.request.query_params.get("metodo_pago_id")

        if sesion_id:
            return MovimientoSelector.get_movimientos_sesion(
                sesion_id=sesion_id,
                tipo=tipo,
                metodo_pago_id=metodo_pago_id,
            )

        queryset = MovimientoCaja.objects.select_related(
            "sesion__caja", "metodo_pago", "usuario"
        )

        if not es_supervisor:
            # Cajero solo ve sus propios movimientos
            queryset = queryset.filter(usuario=user)

        # Filtro de fechas
        fecha_inicio = self.request.query_params.get("fecha_inicio")
        fecha_fin = self.request.query_params.get("fecha_fin")
        if fecha_inicio:
            queryset = queryset.filter(fecha__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__date__lte=fecha_fin)

        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MovimientoCajaDetailSerializer
        return MovimientoCajaListSerializer

    def get_permissions(self):
        return [IsAuthenticated(), EsCajero()]
