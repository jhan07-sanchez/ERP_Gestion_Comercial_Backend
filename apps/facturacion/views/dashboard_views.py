from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta

from apps.facturacion.models import Factura, FacturaDetalle


class DashboardFacturacionViewSet(viewsets.ViewSet):
    """
    API endpoint para analíticas y métricas de facturación (Dashboard).

    Endpoints:
        - GET /dashboard/resumen/            → KPIs del mes actual y desglose por estados.
        - GET /dashboard/ventas-mensuales/    → Evolución de ventas últimos 6 meses.
        - GET /dashboard/top-clientes/        → Top 5 clientes por monto facturado.
        - GET /dashboard/top-productos/       → Top 5 productos más vendidos.
        - GET /dashboard/cuentas-por-cobrar/  → Facturas pendientes de cobro.

    Optimización:
        - Usa aggregate() y annotate() para operaciones en base de datos.
        - select_related() en cuentas por cobrar para evitar N+1.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """
        KPIs generales: total facturado, total cobrado, saldo pendiente
        y desglose por estados (histórico global).
        """
        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)

        facturas_mes = Factura.objects.filter(
            estado__in=["EMITIDA", "PAGADA", "PARCIAL"],
            fecha_emision__gte=inicio_mes
        )

        total_facturado_mes = facturas_mes.aggregate(total=Sum("total"))["total"] or 0
        saldo_pendiente_mes = facturas_mes.aggregate(saldo=Sum("saldo_pendiente"))["saldo"] or 0
        total_cobrado_mes = total_facturado_mes - saldo_pendiente_mes

        estados_count = Factura.objects.values("estado").annotate(cantidad=Count("id"))

        return Response({
            "kpis_mes_actual": {
                "mes": inicio_mes.strftime("%Y-%m"),
                "total_facturado": float(total_facturado_mes),
                "total_cobrado": float(total_cobrado_mes),
                "saldo_pendiente": float(saldo_pendiente_mes),
            },
            "facturas_por_estado": {
                e["estado"]: e["cantidad"] for e in estados_count
            },
        })

    @action(detail=False, methods=["get"], url_path="ventas-mensuales")
    def ventas_mensuales(self, request):
        """Evolución de ventas por mes de los últimos 6 meses."""
        hace_6_meses = timezone.now().date() - timedelta(days=180)

        ventas = (
            Factura.objects.filter(
                estado__in=["EMITIDA", "PAGADA", "PARCIAL"],
                fecha_emision__gte=hace_6_meses,
            )
            .annotate(mes=TruncMonth("fecha_emision"))
            .values("mes")
            .annotate(total_facturado=Sum("total"), cantidad_facturas=Count("id"))
            .order_by("mes")
        )

        return Response([
            {
                "mes": v["mes"].strftime("%Y-%m"),
                "total_facturado": float(v["total_facturado"]),
                "cantidad_facturas": v["cantidad_facturas"],
            }
            for v in ventas
        ])

    @action(detail=False, methods=["get"], url_path="top-clientes")
    def top_clientes(self, request):
        """Top 5 clientes por monto total facturado."""
        clientes = (
            Factura.objects.filter(estado__in=["EMITIDA", "PAGADA", "PARCIAL"])
            .values("cliente__id", "cliente__nombre")
            .annotate(total_comprado=Sum("total"))
            .order_by("-total_comprado")[:5]
        )

        return Response([
            {
                "cliente_id": c["cliente__id"],
                "cliente_nombre": c["cliente__nombre"],
                "total_comprado": float(c["total_comprado"]),
            }
            for c in clientes
        ])

    @action(detail=False, methods=["get"], url_path="top-productos")
    def top_productos(self, request):
        """Top 5 productos más vendidos por cantidad."""
        productos = (
            FacturaDetalle.objects.filter(
                factura__estado__in=["EMITIDA", "PAGADA", "PARCIAL"]
            )
            .values("producto__id", "producto__nombre")
            .annotate(
                cantidad_vendida=Sum("cantidad"),
                monto_generado=Sum("total_linea")
            )
            .order_by("-cantidad_vendida")[:5]
        )

        return Response([
            {
                "producto_id": p["producto__id"],
                "producto_nombre": p["producto__nombre"],
                "cantidad_vendida": float(p["cantidad_vendida"]),
                "monto_generado": float(p["monto_generado"]),
            }
            for p in productos
        ])

    @action(detail=False, methods=["get"], url_path="cuentas-por-cobrar")
    def cuentas_por_cobrar(self, request):
        """Facturas pendientes de cobro ordenadas por antigüedad."""
        pendientes = (
            Factura.objects.filter(estado__in=["EMITIDA", "PARCIAL", "VENCIDA"])
            .exclude(saldo_pendiente__lte=0)
            .select_related("cliente")
            .order_by("fecha_vencimiento", "fecha_emision")[:20]
        )

        return Response([
            {
                "factura_id": f.id,
                "numero": f.numero,
                "cliente_nombre": f.cliente.nombre,
                "fecha_emision": f.fecha_emision,
                "fecha_vencimiento": f.fecha_vencimiento,
                "estado": f.estado,
                "total": float(f.total),
                "saldo_pendiente": float(f.saldo_pendiente),
            }
            for f in pendientes
        ])
