# apps/documentos/views.py
"""
🔗 VIEWS - ENDPOINTS DE DOCUMENTOS
=====================================

Endpoints:
  GET/POST  /api/documentos/compra/{id}/pdf/
  GET/POST  /api/documentos/venta/{id}/factura/
  GET/POST  /api/documentos/venta/{id}/recibo-pos/
  GET/POST  /api/documentos/reportes/ventas/
  GET/POST  /api/documentos/reportes/compras/
  GET/POST  /api/documentos/reportes/inventario/

Todos los endpoints reciben `empresa` en el body (POST)
o como query param `empresa` en base64 (GET).

Ejemplo de request desde frontend:
    POST /api/documentos/compra/1/pdf/
    Content-Type: application/json
    {
        "empresa": {
            "nombre": "FERRESOFT 360 S.A.S",
            "nit": "900123456-7",
            "regimen": "Régimen Común",
            "direccion": "Calle 10 # 5-23",
            "ciudad": "Bogotá D.C.",
            "telefono": "601 234 5678",
            "email": "info@ferresoft.com",
            "logo_base64": "data:image/png;base64,..."
        }
    }
"""

import json
import logging
from base64 import b64decode

from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from apps.auditorias.services.auditoria_service import AuditoriaService

from apps.compras.models import Compra
from apps.ventas.models import Venta
from apps.productos.models import Producto

from .services import (
    generar_pdf_compra,
    generar_pdf_factura,
    generar_recibo_pos,
    generar_reporte_ventas,
    generar_reporte_compras,
    generar_reporte_inventario,
    DocumentoService,
)
from .serializers import (
    DocumentoListSerializer,
    DocumentoDetailSerializer,
)
from .models import Documento

logger = logging.getLogger("documentos")


# ============================================================================
# HELPERS
# ============================================================================


def _empresa_desde_request(request) -> dict:
    """
    Extrae datos de empresa del request.

    Soporta:
    1. POST con body JSON: { "empresa": {...} }
    2. GET con query param `empresa` (JSON string)

    Returns:
        dict: Datos de empresa (puede ser vacío si no se envían)
    """
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
    """
    Crea HttpResponse con el PDF listo para descargar o visualizar.

    Args:
        pdf_buffer: BytesIO con el PDF
        filename: Nombre del archivo para descarga
    """
    response = HttpResponse(
        pdf_buffer.getvalue(),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response


# ============================================================================
# DOCUMENTOS DE COMPRA
# ============================================================================


class CompraDocumentoView(APIView):
    """
    GET/POST /api/documentos/compra/{pk}/pdf/

    Genera PDF oficial de orden de compra.
    Requiere datos de empresa en el body o query param.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return self._generar(request, pk)

    def get(self, request, pk):
        return self._generar(request, pk)

    def _generar(self, request, pk):
        try:
            compra = (
                Compra.objects.select_related("proveedor", "usuario")
                .prefetch_related("detalles__producto")
                .get(pk=pk)
            )

        except Compra.DoesNotExist:
            return Response(
                {"error": f"Compra {pk} no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        empresa = _empresa_desde_request(request)

        try:
            # Asegurar persistencia (Get o Create)
            documento = DocumentoService.obtener_o_crear_desde_compra(compra, request.user)
            
            pdf_buffer = generar_pdf_compra(documento, empresa)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='DESCARGAR',
                modulo='DOCUMENTOS',
                objeto=documento,
                descripcion=f"PDF de Compra generado: {documento.numero_interno}",
                request=request
            )

            logger.info(
                f"✅ PDF Compra {documento.numero_interno} generado por {request.user}"
            )
            return _response_pdf(
                pdf_buffer, filename=f"compra_{documento.numero_interno}.pdf"
            )

        except Exception as e:
            logger.error(f"❌ Error generando PDF compra {pk}: {e}")
            return Response(
                {"error": f"Error al generar PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# DOCUMENTOS DE VENTA
# ============================================================================


class VentaFacturaView(APIView):
    """
    GET/POST /api/documentos/venta/{pk}/factura/

    Genera factura de venta oficial (Colombia DIAN).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return self._generar(request, pk)

    def get(self, request, pk):
        return self._generar(request, pk)

    def _generar(self, request, pk):
        try:
            venta = (
                Venta.objects.select_related("cliente", "usuario")
                .prefetch_related("detalles__producto")
                .get(pk=pk)
            )

        except Venta.DoesNotExist:
            return Response(
                {"error": f"Venta {pk} no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        empresa = _empresa_desde_request(request)

        try:
            # Asegurar persistencia (Get o Create)
            documento = DocumentoService.obtener_o_crear_desde_venta(venta, request.user)
            
            pdf_buffer = generar_pdf_factura(documento, empresa)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='DESCARGAR',
                modulo='DOCUMENTOS',
                objeto=documento,
                descripcion=f"Factura de Venta generada: {documento.numero_interno}",
                request=request
            )

            logger.info(f"✅ Factura {documento.numero_interno} generada por {request.user}")
            return _response_pdf(pdf_buffer, filename=f"factura_{documento.numero_interno}.pdf")

        except Exception as e:
            logger.error(f"❌ Error generando factura venta {pk}: {e}")
            return Response(
                {"error": f"Error al generar PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class VentaReciboPosView(APIView):
    """
    GET/POST /api/documentos/venta/{pk}/recibo-pos/

    Genera recibo POS térmico (80mm) de la venta.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return self._generar(request, pk)

    def get(self, request, pk):
        return self._generar(request, pk)

    def _generar(self, request, pk):
        try:
            venta = (
                Venta.objects.select_related("cliente", "usuario")
                .prefetch_related("detalles__producto")
                .get(pk=pk)
            )

        except Venta.DoesNotExist:
            return Response(
                {"error": f"Venta {pk} no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        empresa = _empresa_desde_request(request)

        try:
            # Asegurar persistencia (Get o Create)
            documento = DocumentoService.obtener_o_crear_desde_venta(venta, request.user)
            
            pdf_buffer = generar_recibo_pos(documento, empresa)
            logger.info(f"✅ Recibo POS {documento.numero_interno} generado por {request.user}")
            return _response_pdf(pdf_buffer, filename=f"recibo_pos_{documento.numero_interno}.pdf")

        except Exception as e:
            logger.error(f"❌ Error generando recibo POS venta {pk}: {e}")
            return Response(
                {"error": f"Error al generar PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ============================================================================
# REPORTES
# ============================================================================


class ReporteVentasView(APIView):
    """
    POST /api/documentos/reportes/ventas/

    Body:
        {
            "empresa": {...},
            "fecha_inicio": "2026-01-01",
            "fecha_fin": "2026-12-31"
        }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})
        fecha_inicio = body.get("fecha_inicio", "")
        fecha_fin = body.get("fecha_fin", "")

        if not fecha_inicio or not fecha_fin:
            return Response(
                {"error": "Se requieren fecha_inicio y fecha_fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ventas_qs = Venta.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        ).select_related("cliente", "usuario")

        try:
            pdf_buffer = generar_reporte_ventas(
                ventas_qs, empresa, fecha_inicio, fecha_fin
            )
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='DESCARGAR',
                modulo='REPORTES',
                descripcion=f"Reporte de Ventas generado: {fecha_inicio} a {fecha_fin}",
                request=request
            )

            return _response_pdf(
                pdf_buffer, filename=f"reporte_ventas_{fecha_inicio}_{fecha_fin}.pdf"
            )
        except Exception as e:
            logger.error(f"❌ Error generando reporte ventas: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporteComprasView(APIView):
    """
    POST /api/documentos/reportes/compras/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})
        fecha_inicio = body.get("fecha_inicio", "")
        fecha_fin = body.get("fecha_fin", "")

        if not fecha_inicio or not fecha_fin:
            return Response(
                {"error": "Se requieren fecha_inicio y fecha_fin"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        compras_qs = Compra.objects.filter(
            fecha__gte=fecha_inicio,
            fecha__lte=fecha_fin,
        ).select_related("proveedor", "usuario")

        try:
            pdf_buffer = generar_reporte_compras(
                compras_qs, empresa, fecha_inicio, fecha_fin
            )
            return _response_pdf(
                pdf_buffer, filename=f"reporte_compras_{fecha_inicio}_{fecha_fin}.pdf"
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ReporteInventarioView(APIView):
    """
    POST /api/documentos/reportes/inventario/
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        body = json.loads(request.body) if request.body else {}
        empresa = body.get("empresa", {})

        productos_qs = Producto.objects.select_related("categoria").all()

        try:
            pdf_buffer = generar_reporte_inventario(productos_qs, empresa)
            return _response_pdf(pdf_buffer, filename="reporte_inventario.pdf")
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
# ============================================================================
# MÓDULO CENTRALIZADO DE DOCUMENTOS
# ============================================================================

from rest_framework import viewsets
from rest_framework.decorators import action


class DocumentoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet centralizado para consulta de documentos (Facturas, Recibos, Compras).
    """
    queryset = Documento.objects.select_related(
        "venta__cliente", 
        "compra__proveedor", 
        "usuario"
    ).prefetch_related("lineas").all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "list":
            return DocumentoListSerializer
        return DocumentoDetailSerializer

    def get_queryset(self):
        """Aplicar filtros por tipo, venta o compra."""
        qs = super().get_queryset()
        tipo = self.request.query_params.get("tipo")
        venta_id = self.request.query_params.get("venta_id")
        compra_id = self.request.query_params.get("compra_id")

        if tipo:
            qs = qs.filter(tipo=tipo)
        if venta_id:
            qs = qs.filter(venta_id=venta_id)
        if compra_id:
            qs = qs.filter(compra_id=compra_id)

        return qs

    @action(detail=True, methods=["get", "post"], url_path="pdf")
    def generar_pdf(self, request, pk=None):
        """Genera el PDF del documento específico."""
        documento = self.get_object()
        empresa = _empresa_desde_request(request)

        try:
            if documento.tipo in [Documento.TipoDocumento.FACTURA_VENTA]:
                pdf_buffer = generar_pdf_factura(documento, empresa)
            elif documento.tipo == Documento.TipoDocumento.TICKET_POS:
                pdf_buffer = generar_recibo_pos(documento, empresa)
            elif documento.tipo == Documento.TipoDocumento.FACTURA_COMPRA:
                pdf_buffer = generar_pdf_compra(documento, empresa)
            else:
                return Response(
                    {"error": "Tipo de documento no soportado para PDF."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='DESCARGAR',
                modulo='DOCUMENTOS',
                objeto=documento,
                descripcion=f"PDF de {documento.get_tipo_display()} generado vía Módulo Central",
                request=request
            )

            return _response_pdf(pdf_buffer, filename=f"{documento.numero_interno}.pdf")

        except Exception as e:
            logger.error(f"❌ Error generando PDF desde módulo central ({documento.id}): {e}")
            return Response(
                {"error": f"Error al generar PDF: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
