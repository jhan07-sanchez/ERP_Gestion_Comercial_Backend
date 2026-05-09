from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from apps.reportes.services.financial_service import FinancialService
from apps.reportes.services.analytics_service import AnalyticsService
from apps.usuarios.permissions import EsSupervisor

class ReporteBaseView(APIView):
    permission_classes = [IsAuthenticated, EsSupervisor]

    def get_params(self, request):
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        sucursal_id = request.query_params.get('sucursal_id')
        return fecha_inicio, fecha_fin, sucursal_id

class BalanceGeneralView(ReporteBaseView):
    def get(self, request):
        data = FinancialService.get_balance_general()
        return Response({"success": True, "data": data})

class EstadoResultadosView(ReporteBaseView):
    def get(self, request):
        inicio, fin, _ = self.get_params(request)
        data = FinancialService.get_estado_resultados(inicio, fin)
        return Response({"success": True, "data": data})

class FlujoCajaView(ReporteBaseView):
    def get(self, request):
        inicio, fin, _ = self.get_params(request)
        data = FinancialService.get_flujo_caja(inicio, fin)
        return Response({"success": True, "data": data})

class ProductividadView(ReporteBaseView):
    def get(self, request):
        inicio, fin, _ = self.get_params(request)
        data = AnalyticsService.get_productividad(inicio, fin)
        return Response({"success": True, "data": data})

class ProyeccionesView(ReporteBaseView):
    def get(self, request):
        data = AnalyticsService.get_proyecciones_ventas()
        return Response({"success": True, "data": data})
