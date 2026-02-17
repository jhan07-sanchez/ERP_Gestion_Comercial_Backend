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

from apps.compras.models import Compra
from apps.ventas.models import Venta
from apps.inventario.models import Producto

from .services import (
    generar_pdf_compra,
    generar_pdf_factura,
    generar_recibo_pos,
    generar_reporte_ventas,
    generar_reporte_compras,
    generar_reporte_inventario,
)

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
            pdf_buffer = generar_pdf_compra(compra, empresa)
            logger.info(
                f"✅ PDF Compra {compra.numero_compra} generado por {request.user}"
            )
            return _response_pdf(
                pdf_buffer, filename=f"compra_{compra.numero_compra}.pdf"
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
            pdf_buffer = generar_pdf_factura(venta, empresa)
            numero = getattr(venta, "numero_venta", f"VT{venta.id:05d}")
            prefijo = empresa.get("prefijo_factura", "FV")
            logger.info(f"✅ Factura {prefijo}{numero} generada por {request.user}")
            return _response_pdf(pdf_buffer, filename=f"factura_{prefijo}{numero}.pdf")

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
            pdf_buffer = generar_recibo_pos(venta, empresa)
            numero = getattr(venta, "numero_venta", venta.id)
            logger.info(f"✅ Recibo POS {numero} generado por {request.user}")
            return _response_pdf(pdf_buffer, filename=f"recibo_pos_{numero}.pdf")

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
# Create your views here.
