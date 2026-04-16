# apps/documentos/views/api.py
import json
import logging
from base64 import b64decode
from django.http import HttpResponse, JsonResponse
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from apps.auditorias.services.auditoria_service import AuditoriaService
from apps.compras.models import Compra
from apps.ventas.models import Venta
from apps.productos.models import Producto

from ..services import (
    generar_pdf_compra, generar_pdf_factura, generar_recibo_pos,
    generar_reporte_ventas, generar_reporte_compras, generar_reporte_inventario,
    DocumentoService,
)
from ..serializers import (
    DocumentoListSerializer, DocumentoDetailSerializer,
)
from ..models import Documento

logger = logging.getLogger("documentos")

def _empresa_desde_request(request) -> dict:
    if request.method == "POST":
        try:
            body = json.loads(request.body)
            return body.get("empresa", {})
        except (json.JSONDecodeError, AttributeError):
            return {}
    elif request.method == "GET":
        empresa_json = request.GET.get("empresa", "")
        if empresa_json:
            try:
                return json.loads(empresa_json)
            except json.JSONDecodeError:
                return {}
    return {}

def _response_pdf(pdf_buffer, filename: str) -> HttpResponse:
    response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

class CompraDocumentoView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk): return self._generar(request, pk)
    def get(self, request, pk): return self._generar(request, pk)
    def _generar(self, request, pk):
        try:
            compra = Compra.objects.select_related("proveedor", "usuario").prefetch_related("detalles__producto").get(pk=pk)
        except Compra.DoesNotExist:
            return Response({"error": f"Compra {pk} no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        empresa = _empresa_desde_request(request)
        try:
            documento = DocumentoService.obtener_o_crear_desde_compra(compra, request.user)
            pdf_buffer = generar_pdf_compra(documento, empresa)
            AuditoriaService.registrar_accion(usuario=request.user, accion='DESCARGAR', modulo='DOCUMENTOS', objeto=documento, descripcion=f"PDF de Compra generado: {documento.numero_interno}", request=request)
            return _response_pdf(pdf_buffer, filename=f"compra_{documento.numero_interno}.pdf")
        except Exception as e:
            logger.error(f"Error generando PDF compra {pk}: {e}")
            return Response({"error": f"Error al generar PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VentaFacturaView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk): return self._generar(request, pk)
    def get(self, request, pk): return self._generar(request, pk)
    def _generar(self, request, pk):
        try:
            venta = Venta.objects.select_related("cliente", "usuario").prefetch_related("detalles__producto").get(pk=pk)
        except Venta.DoesNotExist:
            return Response({"error": f"Venta {pk} no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        empresa = _empresa_desde_request(request)
        try:
            documento = DocumentoService.obtener_o_crear_desde_venta(venta, request.user)
            pdf_buffer = generar_pdf_factura(documento, empresa)
            AuditoriaService.registrar_accion(usuario=request.user, accion='DESCARGAR', modulo='DOCUMENTOS', objeto=documento, descripcion=f"Factura de Venta generada: {documento.numero_interno}", request=request)
            return _response_pdf(pdf_buffer, filename=f"factura_{documento.numero_interno}.pdf")
        except Exception as e:
            logger.error(f"Error generando factura venta {pk}: {e}")
            return Response({"error": f"Error al generar PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VentaReciboPosView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk): return self._generar(request, pk)
    def get(self, request, pk): return self._generar(request, pk)
    def _generar(self, request, pk):
        try:
            venta = Venta.objects.select_related("cliente", "usuario").prefetch_related("detalles__producto").get(pk=pk)
        except Venta.DoesNotExist:
            return Response({"error": f"Venta {pk} no encontrada."}, status=status.HTTP_404_NOT_FOUND)
        empresa = _empresa_desde_request(request)
        try:
            documento = DocumentoService.obtener_o_crear_desde_venta(venta, request.user)
            pdf_buffer = generar_recibo_pos(documento, empresa)
            return _response_pdf(pdf_buffer, filename=f"recibo_pos_{documento.numero_interno}.pdf")
        except Exception as e:
            logger.error(f"Error generando recibo POS venta {pk}: {e}")
            return Response({"error": f"Error al generar PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReporteVentasView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})
        fecha_inicio, fecha_fin = body.get("fecha_inicio", ""), body.get("fecha_fin", "")
        if not fecha_inicio or not fecha_fin: return Response({"error": "Se requieren fechas"}, status=status.HTTP_400_BAD_REQUEST)
        ventas_qs = Venta.objects.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin).select_related("cliente", "usuario")
        try:
            pdf_buffer = generar_reporte_ventas(ventas_qs, empresa, fecha_inicio, fecha_fin)
            AuditoriaService.registrar_accion(usuario=request.user, accion='DESCARGAR', modulo='REPORTES', descripcion=f"Reporte de Ventas generado: {fecha_inicio} a {fecha_fin}", request=request)
            return _response_pdf(pdf_buffer, filename=f"reporte_ventas_{fecha_inicio}_{fecha_fin}.pdf")
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReporteComprasView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})
        fecha_inicio, fecha_fin = body.get("fecha_inicio", ""), body.get("fecha_fin", "")
        if not fecha_inicio or not fecha_fin: return Response({"error": "Se requieren fechas"}, status=status.HTTP_400_BAD_REQUEST)
        compras_qs = Compra.objects.filter(fecha__gte=fecha_inicio, fecha__lte=fecha_fin).select_related("proveedor", "usuario")
        try:
            pdf_buffer = generar_reporte_compras(compras_qs, empresa, fecha_inicio, fecha_fin)
            return _response_pdf(pdf_buffer, filename=f"reporte_compras_{fecha_inicio}_{fecha_fin}.pdf")
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ReporteInventarioView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})
        productos_qs = Producto.objects.select_related("categoria").all()
        try:
            pdf_buffer = generar_reporte_inventario(productos_qs, empresa)
            return _response_pdf(pdf_buffer, filename="reporte_inventario.pdf")
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Documento.objects.select_related("venta__cliente", "compra__proveedor", "usuario").prefetch_related("lineas").all()
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        if self.action == "list": return DocumentoListSerializer
        return DocumentoDetailSerializer
    def get_queryset(self):
        qs = super().get_queryset()
        tipo = self.request.query_params.get("tipo")
        venta_id = self.request.query_params.get("venta_id")
        compra_id = self.request.query_params.get("compra_id")
        if tipo: qs = qs.filter(tipo=tipo)
        if venta_id: qs = qs.filter(venta_id=venta_id)
        if compra_id: qs = qs.filter(compra_id=compra_id)
        return qs
    @action(detail=True, methods=["get", "post"], url_path="pdf")
    def generar_pdf(self, request, pk=None):
        documento = self.get_object()
        empresa = _empresa_desde_request(request)
        try:
            if documento.tipo == Documento.TipoDocumento.FACTURA_VENTA: pdf_buffer = generar_pdf_factura(documento, empresa)
            elif documento.tipo == Documento.TipoDocumento.TICKET_POS: pdf_buffer = generar_recibo_pos(documento, empresa)
            elif documento.tipo == Documento.TipoDocumento.FACTURA_COMPRA: pdf_buffer = generar_pdf_compra(documento, empresa)
            else: return Response({"error": "Tipo no soportado"}, status=status.HTTP_400_BAD_REQUEST)
            AuditoriaService.registrar_accion(usuario=request.user, accion='DESCARGAR', modulo='DOCUMENTOS', objeto=documento, descripcion=f"PDF de {documento.get_tipo_display()} generado", request=request)
            return _response_pdf(pdf_buffer, filename=f"{documento.numero_interno}.pdf")
        except Exception as e:
            return Response({"error": f"Error al generar PDF: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
