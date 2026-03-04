# apps/auditorias/views.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VIEWS DE AUDITORÍA - ERP                                ║
╚══════════════════════════════════════════════════════════════════════════════╝

ENDPOINTS:
══════════
GET  /api/auditorias/logs/              → Listar todos los logs (con filtros)
GET  /api/auditorias/logs/{id}/         → Ver detalle de un log
GET  /api/auditorias/estadisticas/      → KPIs y estadísticas
GET  /api/auditorias/logs/mis-logs/     → Solo los logs del usuario actual
GET  /api/auditorias/logs/por-objeto/   → Logs de un objeto específico

ACCESO:
═══════
Solo usuarios con is_staff=True o rol de Admin pueden ver los logs de otros.
Cualquier usuario puede ver sus propios logs.

Autor: Sistema ERP
"""

import logging
from datetime import timedelta

from django.utils import timezone
from django.db.models import Count, Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from apps.auditorias.models import LogAuditoria
from apps.auditorias.serializers.serializers import (
    LogAuditoriaListSerializer,
    LogAuditoriaDetailSerializer,
)

logger = logging.getLogger("auditorias")


class LogAuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de SOLO LECTURA para los logs de auditoría.

    ReadOnlyModelViewSet provee automáticamente:
    ─────────────────────────────────────────────
      GET /logs/       → list()    → LogAuditoriaListSerializer
      GET /logs/{id}/  → retrieve() → LogAuditoriaDetailSerializer

    FILTROS DISPONIBLES:
    ────────────────────
    ?modulo=VENTAS
    ?accion=CREAR
    ?nivel=ERROR
    ?exitoso=false
    ?usuario_id=5
    ?fecha_inicio=2026-01-01
    ?fecha_fin=2026-01-31
    ?search=texto         → busca en descripcion y usuario_nombre
    ?ordering=-fecha_hora → ordenar por campo
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    # Campos para filtro exacto
    filterset_fields = {
        "modulo": ["exact"],
        "accion": ["exact"],
        "nivel": ["exact"],
        "exitoso": ["exact"],
        "usuario": ["exact"],
        "metodo_http": ["exact"],
    }

    # Campos para búsqueda de texto
    search_fields = ["descripcion", "usuario_nombre", "ip_address", "objeto_repr"]

    # Campos para ordenar
    ordering_fields = ["fecha_hora", "modulo", "accion", "nivel", "duracion_ms"]
    ordering = ["-fecha_hora"]

    def get_queryset(self):
        """
        Filtra los logs según el usuario y parámetros.

        LÓGICA:
        ───────
        - Admin/Staff → puede ver todos los logs
        - Usuario normal → solo ve sus propios logs
        """
        qs = LogAuditoria.objects.select_related("usuario", "content_type")

        # Si no es admin, solo ve sus propios logs
        if not self.request.user.is_staff:
            qs = qs.filter(usuario=self.request.user)

        # Filtros de fecha
        fecha_inicio = self.request.query_params.get("fecha_inicio")
        fecha_fin = self.request.query_params.get("fecha_fin")

        if fecha_inicio:
            try:
                from datetime import datetime

                dt = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                qs = qs.filter(fecha_hora__date__gte=dt.date())
            except ValueError:
                pass

        if fecha_fin:
            try:
                from datetime import datetime

                dt = datetime.strptime(fecha_fin, "%Y-%m-%d")
                qs = qs.filter(fecha_hora__date__lte=dt.date())
            except ValueError:
                pass

        # Filtro por ip
        ip = self.request.query_params.get("ip")
        if ip:
            qs = qs.filter(ip_address=ip)

        return qs

    def get_serializer_class(self):
        """
        Usa serializer diferente según la acción.

        list()     → LogAuditoriaListSerializer (resumido)
        retrieve() → LogAuditoriaDetailSerializer (completo)
        """
        if self.action == "retrieve":
            return LogAuditoriaDetailSerializer
        return LogAuditoriaListSerializer

    @action(detail=False, methods=["get"], url_path="mis-logs")
    def mis_logs(self, request):
        """
        GET /api/auditorias/logs/mis-logs/

        Devuelve solo los logs del usuario autenticado.
        Útil para que cada usuario vea su propio historial.
        """
        qs = LogAuditoria.objects.filter(usuario=request.user).order_by("-fecha_hora")[
            :100
        ]

        serializer = LogAuditoriaListSerializer(qs, many=True)
        return Response(
            {
                "success": True,
                "count": qs.count(),
                "data": serializer.data,
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="por-objeto",
        permission_classes=[IsAdminUser],
    )
    def por_objeto(self, request):
        """
        GET /api/auditorias/logs/por-objeto/?app=ventas&modelo=venta&id=42

        Devuelve todos los logs de un objeto específico.
        Ej: historial completo de la Venta #42.
        """
        from django.contrib.contenttypes.models import ContentType

        app = request.query_params.get("app")
        modelo = request.query_params.get("modelo")
        obj_id = request.query_params.get("id")

        if not all([app, modelo, obj_id]):
            return Response(
                {"error": "Se requieren parámetros: app, modelo, id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ct = ContentType.objects.get(app_label=app, model=modelo.lower())
        except ContentType.DoesNotExist:
            return Response(
                {"error": f"Modelo {app}.{modelo} no existe"},
                status=status.HTTP_404_NOT_FOUND,
            )

        qs = LogAuditoria.objects.filter(content_type=ct, object_id=obj_id).order_by(
            "-fecha_hora"
        )

        serializer = LogAuditoriaDetailSerializer(qs, many=True)
        return Response(
            {
                "success": True,
                "objeto": {"app": app, "modelo": modelo, "id": obj_id},
                "count": qs.count(),
                "data": serializer.data,
            }
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="actividad-usuario",
        permission_classes=[IsAdminUser],
    )
    def actividad_usuario(self, request):
        """
        GET /api/auditorias/logs/actividad-usuario/?usuario_id=5&dias=30

        Historial de actividad de un usuario específico.
        """
        usuario_id = request.query_params.get("usuario_id")
        dias = int(request.query_params.get("dias", 30))

        if not usuario_id:
            return Response({"error": "Se requiere usuario_id"}, status=400)

        desde = timezone.now() - timedelta(days=dias)
        qs = LogAuditoria.objects.filter(
            usuario_id=usuario_id, fecha_hora__gte=desde
        ).order_by("-fecha_hora")

        # Estadísticas del usuario
        stats = qs.aggregate(
            total=Count("id"),
            exitosos=Count("id", filter=Q(exitoso=True)),
            fallidos=Count("id", filter=Q(exitoso=False)),
        )

        serializer = LogAuditoriaListSerializer(qs[:200], many=True)

        return Response(
            {
                "success": True,
                "periodo_dias": dias,
                "estadisticas": stats,
                "logs": serializer.data,
            }
        )


class EstadisticasAuditoriaView(APIView):
    """
    GET /api/auditorias/estadisticas/

    Dashboard de estadísticas de auditoría.
    Solo para administradores.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        try:
            ahora = timezone.now()
            hoy = ahora.date()
            semana_pasada = ahora - timedelta(days=7)

            # Totales generales
            total_logs = LogAuditoria.objects.count()
            logs_hoy = LogAuditoria.objects.filter(fecha_hora__date=hoy).count()
            logs_semana = LogAuditoria.objects.filter(
                fecha_hora__gte=semana_pasada
            ).count()

            # Errores y seguridad hoy
            # Alertas del sistema: Incluye WARNING, ERROR y CRITICAL
            errores_hoy = LogAuditoria.objects.filter(
                fecha_hora__date=hoy, 
                nivel__in=["WARNING", "ERROR", "CRITICAL"]
            ).count()

            # Control de Acceso: Incluye accesos denegados e intentos de login fallidos
            accesos_denegados = LogAuditoria.objects.filter(
                Q(fecha_hora__date=hoy),
                Q(accion="ACCESO_DENEGADO") | Q(accion="LOGIN_FALLIDO")
            ).count()

            logins_fallidos = LogAuditoria.objects.filter(
                fecha_hora__date=hoy, accion="LOGIN_FALLIDO"
            ).count()

            # Usuarios activos hoy (distinct)
            usuarios_activos = (
                LogAuditoria.objects.filter(fecha_hora__date=hoy, usuario__isnull=False)
                .values("usuario")
                .distinct()
                .count()
            )

            # Distribución por módulo (últimos 7 días)
            por_modulo = dict(
                LogAuditoria.objects.filter(fecha_hora__gte=semana_pasada)
                .values("modulo")
                .annotate(total=Count("id"))
                .values_list("modulo", "total")
            )

            # Distribución por acción (últimos 7 días)
            por_accion = dict(
                LogAuditoria.objects.filter(fecha_hora__gte=semana_pasada)
                .values("accion")
                .annotate(total=Count("id"))
                .values_list("accion", "total")
            )

            # Distribución por nivel (últimos 7 días)
            por_nivel = dict(
                LogAuditoria.objects.filter(fecha_hora__gte=semana_pasada)
                .values("nivel")
                .annotate(total=Count("id"))
                .values_list("nivel", "total")
            )

            # Últimas 10 acciones críticas/errores
            actividad_critica = LogAuditoria.objects.filter(
                Q(nivel="ERROR") | Q(nivel="CRITICAL") | Q(nivel="WARNING")
            ).order_by("-fecha_hora")[:10]

            actividad_reciente = LogAuditoriaListSerializer(
                actividad_critica, many=True
            ).data

            data = {
                "total_logs": total_logs,
                "logs_hoy": logs_hoy,
                "logs_semana": logs_semana,
                "errores_hoy": errores_hoy,
                "accesos_denegados": accesos_denegados,
                "logins_fallidos": logins_fallidos,
                "usuarios_activos": usuarios_activos,
                "por_modulo": por_modulo,
                "por_accion": por_accion,
                "por_nivel": por_nivel,
                "actividad_reciente": actividad_reciente,
            }

            return Response({"success": True, "data": data})

        except Exception as e:
            logger.error(f"Error en EstadisticasAuditoriaView: {e}")
            return Response(
                {"success": False, "error": "Error al obtener estadísticas"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
