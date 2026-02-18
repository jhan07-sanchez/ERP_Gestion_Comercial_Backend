# apps/dashboard/views/api.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VIEWS DEL DASHBOARD - ERP                               ║
╚══════════════════════════════════════════════════════════════════════════════╝

Todos los endpoints del dashboard son de SOLO LECTURA (GET).
No crean ni modifican datos — solo consultan y agregan.

Patrón usado: APIView (no ViewSet, porque no hay CRUD estándar).
Cada endpoint es independiente y tiene su propia responsabilidad.

Autor: Sistema ERP
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.dashboard.services import DashboardService
from apps.dashboard.serializers import (
    FiltroFechasSerializer,
    FiltroGraficoSerializer,
    FiltroTopSerializer,
)

logger = logging.getLogger("dashboard")


# ============================================================================
# HELPER: respuesta de error estándar
# ============================================================================


def error_response(mensaje, status_code=status.HTTP_400_BAD_REQUEST):
    return Response({"success": False, "error": mensaje}, status=status_code)


def ok_response(data, mensaje=None):
    resp = {"success": True, "data": data}
    if mensaje:
        resp["mensaje"] = mensaje
    return Response(resp, status=status.HTTP_200_OK)


# ============================================================================
# ENDPOINT 1: RESUMEN GENERAL (tarjetas principales)
# ============================================================================


class ResumenGeneralView(APIView):
    """
    KPIs principales del dashboard.

    Retorna las tarjetas de resumen:
    - Ventas del mes (total + variación vs mes anterior)
    - Compras del mes
    - Ganancia bruta
    - Clientes nuevos
    - Alertas de stock

    GET /api/dashboard/resumen/

    Response:
        {
            "success": true,
            "data": {
                "ventas_mes": { "total": 5000000, "cantidad": 42, "variacion": 12.5 },
                "compras_mes": { "total": 2000000, "cantidad": 10, "variacion": -5.0 },
                "ganancia_mes": { "total": 3000000, "variacion": 25.0 },
                "clientes_nuevos": { "total": 8, "variacion": 33.3 },
                "productos_activos": 120,
                "alertas_stock": 5
            }
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = DashboardService.obtener_resumen_general()
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en ResumenGeneralView: {str(e)}")
            return error_response(
                "Error al obtener el resumen general.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 2: KPIs DE VENTAS
# ============================================================================


class KpisVentasView(APIView):
    """
    Métricas detalladas de ventas con filtro de fechas.

    GET /api/dashboard/ventas/
    GET /api/dashboard/ventas/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31

    Query params:
        fecha_inicio: YYYY-MM-DD (opcional)
        fecha_fin:    YYYY-MM-DD (opcional)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Validar parámetros de entrada
        serializer = FiltroFechasSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        fecha_inicio = serializer.validated_data.get("fecha_inicio")
        fecha_fin = serializer.validated_data.get("fecha_fin")

        # Convertir a string si existen
        fi = fecha_inicio.isoformat() if fecha_inicio else None
        ff = fecha_fin.isoformat() if fecha_fin else None

        try:
            data = DashboardService.obtener_kpis_ventas(fecha_inicio=fi, fecha_fin=ff)
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en KpisVentasView: {str(e)}")
            return error_response(
                "Error al obtener KPIs de ventas.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 3: KPIs DE COMPRAS
# ============================================================================


class KpisComprasView(APIView):
    """
    Métricas detalladas de compras con filtro de fechas.

    GET /api/dashboard/compras/
    GET /api/dashboard/compras/?fecha_inicio=2026-01-01&fecha_fin=2026-01-31
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FiltroFechasSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        fecha_inicio = serializer.validated_data.get("fecha_inicio")
        fecha_fin = serializer.validated_data.get("fecha_fin")
        fi = fecha_inicio.isoformat() if fecha_inicio else None
        ff = fecha_fin.isoformat() if fecha_fin else None

        try:
            data = DashboardService.obtener_kpis_compras(fecha_inicio=fi, fecha_fin=ff)
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en KpisComprasView: {str(e)}")
            return error_response(
                "Error al obtener KPIs de compras.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 4: KPIs DE INVENTARIO
# ============================================================================


class KpisInventarioView(APIView):
    """
    Estado actual del inventario.

    GET /api/dashboard/inventario/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = DashboardService.obtener_kpis_inventario()
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en KpisInventarioView: {str(e)}")
            return error_response(
                "Error al obtener KPIs de inventario.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 5: KPIs DE CLIENTES
# ============================================================================


class KpisClientesView(APIView):
    """
    Métricas de la base de clientes.

    GET /api/dashboard/clientes/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = DashboardService.obtener_kpis_clientes()
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en KpisClientesView: {str(e)}")
            return error_response(
                "Error al obtener KPIs de clientes.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 6: GRÁFICO DE VENTAS
# ============================================================================


class GraficoVentasView(APIView):
    """
    Datos para el gráfico de ventas (para Chart.js, Recharts, etc.).

    GET /api/dashboard/graficos/ventas/
    GET /api/dashboard/graficos/ventas/?periodo=mes&agrupacion=dia

    Query params:
        periodo:    semana | mes | año  (default: mes)
        agrupacion: dia | semana | mes  (default: dia)

    Response:
        {
            "success": true,
            "data": [
                { "fecha": "2026-01-15", "total": 1500000, "cantidad": 5 },
                { "fecha": "2026-01-16", "total": 2300000, "cantidad": 8 },
                ...
            ]
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FiltroGraficoSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        periodo = serializer.validated_data.get("periodo", "mes")
        agrupacion = serializer.validated_data.get("agrupacion", "dia")

        try:
            data = DashboardService.obtener_grafico_ventas(
                periodo=periodo, agrupacion=agrupacion
            )
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en GraficoVentasView: {str(e)}")
            return error_response(
                "Error al obtener datos del gráfico de ventas.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 7: GRÁFICO DE COMPRAS
# ============================================================================


class GraficoComprasView(APIView):
    """
    Datos para el gráfico de compras.

    GET /api/dashboard/graficos/compras/
    GET /api/dashboard/graficos/compras/?periodo=mes&agrupacion=dia
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FiltroGraficoSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        periodo = serializer.validated_data.get("periodo", "mes")
        agrupacion = serializer.validated_data.get("agrupacion", "dia")

        try:
            data = DashboardService.obtener_grafico_compras(
                periodo=periodo, agrupacion=agrupacion
            )
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en GraficoComprasView: {str(e)}")
            return error_response(
                "Error al obtener datos del gráfico de compras.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 8: TOP PRODUCTOS
# ============================================================================


class ProductosTopView(APIView):
    """
    Top N productos más vendidos.

    GET /api/dashboard/top/productos/
    GET /api/dashboard/top/productos/?limite=10&fecha_inicio=2026-01-01&fecha_fin=2026-01-31
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FiltroTopSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        limite = serializer.validated_data.get("limite", 10)
        fi = serializer.validated_data.get("fecha_inicio")
        ff = serializer.validated_data.get("fecha_fin")

        try:
            data = DashboardService.obtener_productos_top(
                limite=limite,
                fecha_inicio=fi.isoformat() if fi else None,
                fecha_fin=ff.isoformat() if ff else None,
            )
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en ProductosTopView: {str(e)}")
            return error_response(
                "Error al obtener top de productos.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 9: TOP CLIENTES
# ============================================================================


class ClientesTopView(APIView):
    """
    Top N clientes por monto comprado.

    GET /api/dashboard/top/clientes/
    GET /api/dashboard/top/clientes/?limite=10&fecha_inicio=2026-01-01&fecha_fin=2026-01-31
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = FiltroTopSerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response(serializer.errors)

        limite = serializer.validated_data.get("limite", 10)
        fi = serializer.validated_data.get("fecha_inicio")
        ff = serializer.validated_data.get("fecha_fin")

        try:
            data = DashboardService.obtener_clientes_top(
                limite=limite,
                fecha_inicio=fi.isoformat() if fi else None,
                fecha_fin=ff.isoformat() if ff else None,
            )
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en ClientesTopView: {str(e)}")
            return error_response(
                "Error al obtener top de clientes.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# ENDPOINT 10: ALERTAS
# ============================================================================


class AlertasView(APIView):
    """
    Alertas activas del sistema.

    GET /api/dashboard/alertas/

    Response:
        {
            "success": true,
            "data": {
                "total": 8,
                "sin_stock": [...],
                "stock_bajo": [...],
                "ventas_pendientes": [...]
            }
        }
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            data = DashboardService.obtener_alertas()
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en AlertasView: {str(e)}")
            return error_response(
                "Error al obtener alertas.", status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# ENDPOINT 11: ACTIVIDAD RECIENTE
# ============================================================================


class ActividadRecienteView(APIView):
    """
    Últimas transacciones del sistema (feed de actividad).

    GET /api/dashboard/actividad/
    GET /api/dashboard/actividad/?limite=20
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        limite = request.query_params.get("limite", 10)
        try:
            limite = int(limite)
            if limite < 1 or limite > 50:
                return error_response("El límite debe estar entre 1 y 50.")
        except ValueError:
            return error_response("El parámetro 'limite' debe ser un número entero.")

        try:
            data = DashboardService.obtener_actividad_reciente(limite=limite)
            return ok_response(data)
        except Exception as e:
            logger.error(f"Error en ActividadRecienteView: {str(e)}")
            return error_response(
                "Error al obtener la actividad reciente.",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
