from django.db.models import Sum, F, Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from apps.ventas.models import Venta
from apps.inventario.models import Inventario
from apps.caja.models import MovimientoCaja, Caja
from decimal import Decimal

class FinancialService:
    """
    Servicio especializado en cálculos financieros enterprise:
    - Balance General
    - Estado de Resultados
    - Flujo de Caja
    """

    @staticmethod
    def get_balance_general():
        """
        Calcula el Balance General (Activos, Pasivos, Patrimonio)
        Activos = Efectivo en Cajas + Valorización de Inventario
        Pasivos = Cuentas por pagar (derivadas de compras a crédito)
        Patrimonio = Activos - Pasivos
        """
        # 1. Efectivo en Cajas (Calculado desde movimientos reales)
        ingresos = MovimientoCaja.objects.filter(
            tipo__in=["APERTURA", "INGRESO_VENTA", "INGRESO_MANUAL"]
        ).aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        
        egresos = MovimientoCaja.objects.filter(
            tipo__in=["EGRESO_COMPRA", "EGRESO_GASTO", "EGRESO_RETIRO"]
        ).aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        
        efectivo_caja = ingresos - egresos

        # 2. Valorización de Inventario (Costo de adquisición)
        valor_inventario = Inventario.objects.aggregate(
            v=Sum(F("stock_actual") * F("producto__precio_compra"))
        )["v"] or Decimal("0.00")
        
        activos_corrientes = float(efectivo_caja + valor_inventario)
        
        # 3. Pasivos Corrientes (Compras con método de pago tipo 'CREDITO')
        # Buscamos compras que no han generado un movimiento de egreso en caja completo
        # O simplemente consultamos el saldo de cuentas por pagar si existiera el modelo.
        # Por ahora lo calculamos como compras totales - pagos realizados en caja.
        from apps.compras.models import Compra
        total_compras = Compra.objects.filter(estado="RECIBIDA").aggregate(s=Sum("total"))["s"] or Decimal("0.00")
        pagos_compras = MovimientoCaja.objects.filter(tipo="EGRESO_COMPRA").aggregate(s=Sum("monto"))["s"] or Decimal("0.00")
        
        pasivos_corrientes = float(max(Decimal("0.00"), total_compras - pagos_compras))
        
        return {
            "activos": {
                "disponible": float(efectivo_caja),
                "inventarios": float(valor_inventario),
                "total_corrientes": activos_corrientes,
                "total": activos_corrientes
            },
            "pasivos": {
                "cuentasPorPagar": pasivos_corrientes,
                "total": pasivos_corrientes
            },
            "patrimonio": activos_corrientes - pasivos_corrientes,
            "fecha_corte": timezone.now().isoformat()
        }

    @staticmethod
    def get_estado_resultados(fecha_inicio=None, fecha_fin=None):
        """
        Calcula el Estado de Resultados (Ingresos, Costos, Utilidad)
        """
        query_ventas = Q(estado="COMPLETADA")
        query_movs = Q()
        
        if fecha_inicio:
            query_ventas &= Q(fecha__gte=fecha_inicio)
            query_movs &= Q(fecha__gte=fecha_inicio)
        if fecha_fin:
            query_ventas &= Q(fecha__lte=fecha_fin)
            query_movs &= Q(fecha__lte=fecha_fin)

        # Ingresos
        ventas = Venta.objects.filter(query_ventas)
        ingresos_totales = float(ventas.aggregate(s=Sum("total"))["s"] or 0)
        
        # Costos (COGS)
        # Suma de (cantidad * precio_compra) de cada detalle de venta completada
        from apps.ventas.models import DetalleVenta
        costos_ventas = float(DetalleVenta.objects.filter(
            venta__in=ventas
        ).aggregate(
            c=Sum(F("cantidad") * F("producto__precio_compra"))
        )["c"] or 0)
        
        # Gastos Operativos (Egresos de caja tipo GASTO)
        gastos_operativos = float(MovimientoCaja.objects.filter(
            query_movs,
            tipo="EGRESO_GASTO"
        ).aggregate(s=Sum("monto"))["s"] or 0)
        
        utilidad_bruta = ingresos_totales - costos_ventas
        utilidad_neta = utilidad_bruta - gastos_operativos
        
        return {
            "ingresos": ingresos_totales,
            "costos": costos_ventas,
            "gastos": gastos_operativos,
            "utilidad_bruta": utilidad_bruta,
            "utilidad_neta": utilidad_neta,
            "margen_bruto": (utilidad_bruta / ingresos_totales * 100) if ingresos_totales > 0 else 0,
            "periodo": {
                "inicio": fecha_inicio,
                "fin": fecha_fin
            }
        }

    @staticmethod
    def get_flujo_caja(fecha_inicio=None, fecha_fin=None):
        """
        Calcula el Flujo de Caja (Entradas vs Salidas)
        """
        query = Q()
        if fecha_inicio: query &= Q(fecha__gte=fecha_inicio)
        if fecha_fin: query &= Q(fecha__lte=fecha_fin)
        
        movimientos = MovimientoCaja.objects.filter(query)
        
        entradas = float(movimientos.filter(
            tipo__in=["APERTURA", "INGRESO_VENTA", "INGRESO_MANUAL"]
        ).aggregate(s=Sum("monto"))["s"] or 0)
        
        salidas = float(movimientos.filter(
            tipo__in=["EGRESO_COMPRA", "EGRESO_GASTO", "EGRESO_RETIRO"]
        ).aggregate(s=Sum("monto"))["s"] or 0)
        
        return {
            "entradas": entradas,
            "salidas": salidas,
            "balance": entradas - salidas,
            "detalle": [
                {
                    "tipo": m.tipo,
                    "monto": float(m.monto),
                    "fecha": m.fecha.isoformat(),
                    "concepto": m.descripcion
                }
                for m in movimientos.order_by("-fecha")[:50] # Top 50 para no saturar
            ]
        }
