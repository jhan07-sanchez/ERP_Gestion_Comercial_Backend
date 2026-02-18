# apps/dashboard/services/dashboard_service.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SERVICIO DE DASHBOARD - KPIs ERP                        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Este servicio centraliza todos los cálculos de KPIs del ERP.
Consulta datos de: Ventas, Compras, Inventario, Caja y Clientes.

¿Por qué un servicio separado?
- Mantiene las vistas (views) limpias y simples
- Facilita el testing unitario de la lógica
- Permite reutilizar los cálculos desde distintos lugares
- Separa la responsabilidad: la vista recibe, el servicio calcula

Autor: Sistema ERP
Versión: 1.0
"""

from datetime import date, timedelta, datetime
from django.db.models import (
    Sum,
    Count,
    Avg,
    F,
    Q,
    DecimalField,
    IntegerField,
    ExpressionWrapper,
)
from django.db.models.functions import TruncDay, TruncMonth, TruncWeek
from django.utils import timezone

# Importamos los modelos de otras apps
from apps.ventas.models import Venta, DetalleVenta
from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto, Inventario, Categoria
from apps.clientes.models import Cliente
from apps.caja.models import MovimientoCaja


# ============================================================================
# HELPERS INTERNOS
# ============================================================================


def _rango_hoy():
    """Retorna inicio y fin del día de hoy (con zona horaria)"""
    hoy = timezone.now().date()
    inicio = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
    fin = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
    return inicio, fin


def _rango_mes_actual():
    """Retorna inicio y fin del mes actual"""
    hoy = timezone.now().date()
    inicio = hoy.replace(day=1)
    # Último día del mes
    if hoy.month == 12:
        fin = hoy.replace(day=31)
    else:
        fin = hoy.replace(month=hoy.month + 1, day=1) - timedelta(days=1)
    inicio_dt = timezone.make_aware(datetime.combine(inicio, datetime.min.time()))
    fin_dt = timezone.make_aware(datetime.combine(fin, datetime.max.time()))
    return inicio_dt, fin_dt


def _rango_mes_anterior():
    """Retorna inicio y fin del mes anterior"""
    hoy = timezone.now().date()
    primer_dia_mes_actual = hoy.replace(day=1)
    ultimo_dia_mes_ant = primer_dia_mes_actual - timedelta(days=1)
    primer_dia_mes_ant = ultimo_dia_mes_ant.replace(day=1)
    inicio_dt = timezone.make_aware(
        datetime.combine(primer_dia_mes_ant, datetime.min.time())
    )
    fin_dt = timezone.make_aware(
        datetime.combine(ultimo_dia_mes_ant, datetime.max.time())
    )
    return inicio_dt, fin_dt


def _variacion_porcentual(actual, anterior):
    """
    Calcula la variación porcentual entre dos valores.
    Retorna 0 si el valor anterior es 0 (evita división por cero).
    """
    if anterior == 0:
        return 100.0 if actual > 0 else 0.0
    return round(((actual - anterior) / anterior) * 100, 2)


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================


class DashboardService:
    """
    Servicio central para calcular todos los KPIs del Dashboard.

    Métodos disponibles:
    - obtener_resumen_general()      → KPIs principales del día/mes
    - obtener_kpis_ventas()          → Métricas detalladas de ventas
    - obtener_kpis_compras()         → Métricas detalladas de compras
    - obtener_kpis_inventario()      → Estado del inventario
    - obtener_kpis_clientes()        → Métricas de clientes
    - obtener_grafico_ventas()       → Datos para gráfico de ventas
    - obtener_grafico_compras()      → Datos para gráfico de compras
    - obtener_productos_top()        → Top productos más vendidos
    - obtener_clientes_top()         → Top clientes por compras
    - obtener_alertas()              → Alertas del sistema (stock bajo, etc.)
    - obtener_actividad_reciente()   → Últimas transacciones
    """

    # ========================================================================
    # RESUMEN GENERAL
    # ========================================================================

    @staticmethod
    def obtener_resumen_general():
        """
        KPIs principales para las tarjetas del dashboard.

        Retorna métricas del MES ACTUAL vs MES ANTERIOR para calcular
        la variación (flecha arriba/abajo en el frontend).

        Returns:
            dict: {
                ventas_mes: { total, cantidad, variacion },
                compras_mes: { total, cantidad, variacion },
                ganancia_mes: { total, variacion },
                clientes_nuevos: { total, variacion },
                productos_activos: int,
                alertas_stock: int
            }
        """
        inicio_mes, fin_mes = _rango_mes_actual()
        inicio_ant, fin_ant = _rango_mes_anterior()

        # ── VENTAS MES ACTUAL ──────────────────────────────────────────────
        ventas_mes = Venta.objects.filter(
            fecha__range=(inicio_mes, fin_mes), estado="COMPLETADA"
        )
        total_ventas_mes = ventas_mes.aggregate(total=Sum("total"))["total"] or 0
        cantidad_ventas_mes = ventas_mes.count()

        # ── VENTAS MES ANTERIOR ────────────────────────────────────────────
        ventas_ant = Venta.objects.filter(
            fecha__range=(inicio_ant, fin_ant), estado="COMPLETADA"
        )
        total_ventas_ant = ventas_ant.aggregate(total=Sum("total"))["total"] or 0

        # ── COMPRAS MES ACTUAL ─────────────────────────────────────────────
        compras_mes = Compra.objects.filter(
            fecha__range=(inicio_mes, fin_mes), estado="RECIBIDA"
        )
        total_compras_mes = compras_mes.aggregate(total=Sum("total"))["total"] or 0
        cantidad_compras_mes = compras_mes.count()

        # ── COMPRAS MES ANTERIOR ───────────────────────────────────────────
        compras_ant = Compra.objects.filter(
            fecha__range=(inicio_ant, fin_ant), estado="RECIBIDA"
        )
        total_compras_ant = compras_ant.aggregate(total=Sum("total"))["total"] or 0

        # ── GANANCIA = VENTAS - COMPRAS ───────────────────────────────────
        ganancia_mes = float(total_ventas_mes) - float(total_compras_mes)
        ganancia_ant = float(total_ventas_ant) - float(total_compras_ant)

        # ── CLIENTES NUEVOS ────────────────────────────────────────────────
        clientes_nuevos_mes = Cliente.objects.filter(
            fecha_creacion__range=(inicio_mes, fin_mes)
        ).count()
        clientes_nuevos_ant = Cliente.objects.filter(
            fecha_creacion__range=(inicio_ant, fin_ant)
        ).count()

        # ── ESTADO DEL INVENTARIO ──────────────────────────────────────────
        productos_activos = Producto.objects.filter(estado=True).count()
        alertas_stock = Inventario.objects.filter(
            stock_actual__lte=F("producto__stock_minimo")
        ).count()

        return {
            "ventas_mes": {
                "total": float(total_ventas_mes),
                "cantidad": cantidad_ventas_mes,
                "variacion": _variacion_porcentual(total_ventas_mes, total_ventas_ant),
                "label": "Ventas del mes",
                "icono": "shopping-cart",
                "color": "green",
            },
            "compras_mes": {
                "total": float(total_compras_mes),
                "cantidad": cantidad_compras_mes,
                "variacion": _variacion_porcentual(
                    total_compras_mes, total_compras_ant
                ),
                "label": "Compras del mes",
                "icono": "package",
                "color": "blue",
            },
            "ganancia_mes": {
                "total": ganancia_mes,
                "variacion": _variacion_porcentual(ganancia_mes, ganancia_ant),
                "label": "Ganancia bruta",
                "icono": "trending-up",
                "color": "purple",
            },
            "clientes_nuevos": {
                "total": clientes_nuevos_mes,
                "variacion": _variacion_porcentual(
                    clientes_nuevos_mes, clientes_nuevos_ant
                ),
                "label": "Clientes nuevos",
                "icono": "users",
                "color": "orange",
            },
            "productos_activos": productos_activos,
            "alertas_stock": alertas_stock,
        }

    # ========================================================================
    # KPIs DETALLADOS DE VENTAS
    # ========================================================================

    @staticmethod
    def obtener_kpis_ventas(fecha_inicio=None, fecha_fin=None):
        """
        Métricas completas de ventas para el período indicado.

        Args:
            fecha_inicio: str 'YYYY-MM-DD' (opcional, default = mes actual)
            fecha_fin:    str 'YYYY-MM-DD' (opcional, default = hoy)

        Returns:
            dict con todas las métricas de ventas
        """
        # Parsear fechas o usar mes actual por defecto
        if fecha_inicio and fecha_fin:
            inicio = timezone.make_aware(datetime.strptime(fecha_inicio, "%Y-%m-%d"))
            fin = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(fecha_fin, "%Y-%m-%d").date(), datetime.max.time()
                )
            )
        else:
            inicio, fin = _rango_mes_actual()

        ventas = Venta.objects.filter(fecha__range=(inicio, fin))

        # Totales generales
        total_ventas = ventas.aggregate(total=Sum("total"))["total"] or 0
        promedio_venta = (
            ventas.filter(estado="COMPLETADA").aggregate(prom=Avg("total"))["prom"] or 0
        )

        # Por estado
        por_estado = (
            ventas.values("estado")
            .annotate(cantidad=Count("id"), total=Sum("total"))
            .order_by("estado")
        )

        # Ticket promedio
        completadas = ventas.filter(estado="COMPLETADA")
        ticket_promedio = completadas.aggregate(prom=Avg("total"))["prom"] or 0

        return {
            "periodo": {
                "inicio": inicio.date().isoformat(),
                "fin": fin.date().isoformat(),
            },
            "totales": {
                "monto_total": float(total_ventas),
                "cantidad_total": ventas.count(),
                "ticket_promedio": float(ticket_promedio),
            },
            "por_estado": [
                {
                    "estado": item["estado"],
                    "cantidad": item["cantidad"],
                    "total": float(item["total"] or 0),
                }
                for item in por_estado
            ],
            "completadas": {
                "cantidad": completadas.count(),
                "total": float(completadas.aggregate(t=Sum("total"))["t"] or 0),
            },
            "canceladas": {
                "cantidad": ventas.filter(estado="CANCELADA").count(),
            },
            "pendientes": {
                "cantidad": ventas.filter(estado="PENDIENTE").count(),
            },
        }

    # ========================================================================
    # KPIs DETALLADOS DE COMPRAS
    # ========================================================================

    @staticmethod
    def obtener_kpis_compras(fecha_inicio=None, fecha_fin=None):
        """
        Métricas completas de compras para el período indicado.
        """
        if fecha_inicio and fecha_fin:
            inicio = timezone.make_aware(datetime.strptime(fecha_inicio, "%Y-%m-%d"))
            fin = timezone.make_aware(
                datetime.combine(
                    datetime.strptime(fecha_fin, "%Y-%m-%d").date(), datetime.max.time()
                )
            )
        else:
            inicio, fin = _rango_mes_actual()

        compras = Compra.objects.filter(fecha__range=(inicio, fin))
        recibidas = compras.filter(estado="RECIBIDA")

        total_compras = recibidas.aggregate(t=Sum("total"))["t"] or 0
        ticket_promedio = recibidas.aggregate(p=Avg("total"))["p"] or 0

        por_estado = (
            compras.values("estado")
            .annotate(cantidad=Count("id"), total=Sum("total"))
            .order_by("estado")
        )

        return {
            "periodo": {
                "inicio": inicio.date().isoformat(),
                "fin": fin.date().isoformat(),
            },
            "totales": {
                "monto_total": float(total_compras),
                "cantidad_total": compras.count(),
                "ticket_promedio": float(ticket_promedio),
            },
            "por_estado": [
                {
                    "estado": item["estado"],
                    "cantidad": item["cantidad"],
                    "total": float(item["total"] or 0),
                }
                for item in por_estado
            ],
        }

    # ========================================================================
    # KPIs DE INVENTARIO
    # ========================================================================

    @staticmethod
    def obtener_kpis_inventario():
        """
        Estado actual del inventario.

        Returns:
            dict con métricas del inventario:
            - total_productos, productos_activos, sin_stock, stock_bajo
            - valor_costo, valor_venta, ganancia_potencial
            - por_categoria (lista)
        """
        inventarios = Inventario.objects.select_related(
            "producto", "producto__categoria"
        )

        # Conteos
        total_productos = Producto.objects.count()
        productos_activos = Producto.objects.filter(estado=True).count()
        sin_stock = inventarios.filter(stock_actual=0).count()
        stock_bajo = inventarios.filter(
            stock_actual__gt=0, stock_actual__lte=F("producto__stock_minimo")
        ).count()
        stock_ok = inventarios.filter(
            stock_actual__gt=F("producto__stock_minimo")
        ).count()

        # Valores económicos
        valor_costo = 0
        valor_venta = 0
        for inv in inventarios:
            valor_costo += float(inv.stock_actual * inv.producto.precio_compra)
            valor_venta += float(inv.stock_actual * inv.producto.precio_venta)

        ganancia_potencial = valor_venta - valor_costo

        # Por categoría
        categorias = (
            Categoria.objects.annotate(
                total_stock=Sum("productos__inventario__stock_actual"),
                total_productos=Count("productos", filter=Q(productos__estado=True)),
            )
            .values("nombre", "total_stock", "total_productos")
            .order_by("-total_stock")
        )

        return {
            "conteos": {
                "total_productos": total_productos,
                "productos_activos": productos_activos,
                "sin_stock": sin_stock,
                "stock_bajo": stock_bajo,
                "stock_ok": stock_ok,
            },
            "valores": {
                "valor_costo": round(valor_costo, 2),
                "valor_venta": round(valor_venta, 2),
                "ganancia_potencial": round(ganancia_potencial, 2),
                "margen_porcentaje": round(
                    (ganancia_potencial / valor_costo * 100) if valor_costo > 0 else 0,
                    2,
                ),
            },
            "por_categoria": [
                {
                    "nombre": cat["nombre"],
                    "total_stock": cat["total_stock"] or 0,
                    "total_productos": cat["total_productos"],
                }
                for cat in categorias
            ],
        }

    # ========================================================================
    # KPIs DE CLIENTES
    # ========================================================================

    @staticmethod
    def obtener_kpis_clientes():
        """
        Métricas sobre la base de clientes.
        """
        total_clientes = Cliente.objects.count()
        clientes_activos = Cliente.objects.filter(activo=True).count()

        inicio_mes, fin_mes = _rango_mes_actual()
        nuevos_este_mes = Cliente.objects.filter(
            fecha_creacion__range=(inicio_mes, fin_mes)
        ).count()

        # Cliente con más compras (ventas completadas)
        top_cliente = (
            Cliente.objects.annotate(
                total_comprado=Sum(
                    "ventas__total", filter=Q(ventas__estado="COMPLETADA")
                ),
                cantidad_ventas=Count("ventas", filter=Q(ventas__estado="COMPLETADA")),
            )
            .order_by("-total_comprado")
            .first()
        )

        return {
            "total_clientes": total_clientes,
            "clientes_activos": clientes_activos,
            "nuevos_este_mes": nuevos_este_mes,
            "top_cliente": {
                "nombre": top_cliente.nombre if top_cliente else None,
                "total_comprado": float(top_cliente.total_comprado or 0)
                if top_cliente
                else 0,
                "cantidad_ventas": top_cliente.cantidad_ventas if top_cliente else 0,
            }
            if top_cliente
            else None,
        }

    # ========================================================================
    # DATOS PARA GRÁFICOS
    # ========================================================================

    @staticmethod
    def obtener_grafico_ventas(periodo="mes", agrupacion="dia"):
        """
        Datos para el gráfico de ventas (línea o barras).

        Args:
            periodo:    'semana' | 'mes' | 'año'
            agrupacion: 'dia' | 'semana' | 'mes'

        Returns:
            Lista de { fecha, total, cantidad } para graficar
        """
        hoy = timezone.now()

        # Determinar rango según período
        if periodo == "semana":
            inicio = hoy - timedelta(days=7)
        elif periodo == "año":
            inicio = hoy - timedelta(days=365)
        else:  # mes por defecto
            inicio = hoy - timedelta(days=30)

        ventas = Venta.objects.filter(fecha__gte=inicio, estado="COMPLETADA")

        # Agrupar según la agrupación solicitada
        if agrupacion == "mes":
            ventas = ventas.annotate(periodo=TruncMonth("fecha"))
        elif agrupacion == "semana":
            ventas = ventas.annotate(periodo=TruncWeek("fecha"))
        else:  # dia por defecto
            ventas = ventas.annotate(periodo=TruncDay("fecha"))

        datos = (
            ventas.values("periodo")
            .annotate(total=Sum("total"), cantidad=Count("id"))
            .order_by("periodo")
        )

        return [
            {
                "fecha": item["periodo"].date().isoformat(),
                "total": float(item["total"] or 0),
                "cantidad": item["cantidad"],
            }
            for item in datos
        ]

    @staticmethod
    def obtener_grafico_compras(periodo="mes", agrupacion="dia"):
        """
        Datos para el gráfico de compras (idéntico a ventas pero con Compra).
        """
        hoy = timezone.now()

        if periodo == "semana":
            inicio = hoy - timedelta(days=7)
        elif periodo == "año":
            inicio = hoy - timedelta(days=365)
        else:
            inicio = hoy - timedelta(days=30)

        compras = Compra.objects.filter(fecha__gte=inicio, estado="RECIBIDA")

        if agrupacion == "mes":
            compras = compras.annotate(periodo=TruncMonth("fecha"))
        elif agrupacion == "semana":
            compras = compras.annotate(periodo=TruncWeek("fecha"))
        else:
            compras = compras.annotate(periodo=TruncDay("fecha"))

        datos = (
            compras.values("periodo")
            .annotate(total=Sum("total"), cantidad=Count("id"))
            .order_by("periodo")
        )

        return [
            {
                "fecha": item["periodo"].date().isoformat(),
                "total": float(item["total"] or 0),
                "cantidad": item["cantidad"],
            }
            for item in datos
        ]

    # ========================================================================
    # TOP PRODUCTOS Y CLIENTES
    # ========================================================================

    @staticmethod
    def obtener_productos_top(limite=10, fecha_inicio=None, fecha_fin=None):
        """
        Top N productos más vendidos por cantidad y por monto.

        Args:
            limite: Número de productos a retornar (default 10)
            fecha_inicio, fecha_fin: Filtro opcional de fechas
        """
        filtros = Q(venta__estado="COMPLETADA")

        if fecha_inicio:
            filtros &= Q(
                venta__fecha__gte=timezone.make_aware(
                    datetime.strptime(fecha_inicio, "%Y-%m-%d")
                )
            )
        if fecha_fin:
            filtros &= Q(
                venta__fecha__lte=timezone.make_aware(
                    datetime.combine(
                        datetime.strptime(fecha_fin, "%Y-%m-%d").date(),
                        datetime.max.time(),
                    )
                )
            )

        top = (
            DetalleVenta.objects.filter(filtros)
            .values(
                "producto__id",
                "producto__nombre",
                "producto__codigo",
                "producto__categoria__nombre",
            )
            .annotate(
                total_unidades=Sum("cantidad"),
                total_monto=Sum("subtotal"),
                veces_vendido=Count("venta", distinct=True),
            )
            .order_by("-total_unidades")[:limite]
        )

        return [
            {
                "id": item["producto__id"],
                "codigo": item["producto__codigo"],
                "nombre": item["producto__nombre"],
                "categoria": item["producto__categoria__nombre"],
                "total_unidades": item["total_unidades"],
                "total_monto": float(item["total_monto"] or 0),
                "veces_vendido": item["veces_vendido"],
            }
            for item in top
        ]

    @staticmethod
    def obtener_clientes_top(limite=10, fecha_inicio=None, fecha_fin=None):
        """
        Top N clientes por monto total comprado.
        """
        filtros = Q(ventas__estado="COMPLETADA")

        if fecha_inicio:
            filtros &= Q(
                ventas__fecha__gte=timezone.make_aware(
                    datetime.strptime(fecha_inicio, "%Y-%m-%d")
                )
            )
        if fecha_fin:
            filtros &= Q(
                ventas__fecha__lte=timezone.make_aware(
                    datetime.combine(
                        datetime.strptime(fecha_fin, "%Y-%m-%d").date(),
                        datetime.max.time(),
                    )
                )
            )

        top = (
            Cliente.objects.filter(filtros)
            .annotate(
                total_comprado=Sum(
                    "ventas__total", filter=Q(ventas__estado="COMPLETADA")
                ),
                cantidad_compras=Count("ventas", filter=Q(ventas__estado="COMPLETADA")),
            )
            .order_by("-total_comprado")[:limite]
        )

        return [
            {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "documento": cliente.documento,
                "total_comprado": float(cliente.total_comprado or 0),
                "cantidad_compras": cliente.cantidad_compras,
            }
            for cliente in top
        ]

    # ========================================================================
    # ALERTAS DEL SISTEMA
    # ========================================================================

    @staticmethod
    def obtener_alertas():
        """
        Alertas activas del sistema para mostrar en el dashboard.

        Tipos de alertas:
        - STOCK_BAJO: productos con stock <= stock_mínimo
        - SIN_STOCK: productos con stock = 0
        - VENTAS_PENDIENTES: ventas que llevan más de 24h pendientes

        Returns:
            dict con listas de alertas por tipo
        """
        # Productos sin stock
        sin_stock = (
            Inventario.objects.filter(stock_actual=0, producto__estado=True)
            .select_related("producto", "producto__categoria")
            .values(
                "producto__id",
                "producto__nombre",
                "producto__codigo",
                "producto__categoria__nombre",
            )[:20]
        )

        # Productos con stock bajo (stock <= mínimo pero > 0)
        stock_bajo = (
            Inventario.objects.filter(
                stock_actual__gt=0,
                stock_actual__lte=F("producto__stock_minimo"),
                producto__estado=True,
            )
            .select_related("producto")
            .values(
                "producto__id",
                "producto__nombre",
                "producto__codigo",
                "stock_actual",
                "producto__stock_minimo",
            )[:20]
        )

        # Ventas pendientes hace más de 24 horas
        hace_24h = timezone.now() - timedelta(hours=24)
        ventas_pendientes = (
            Venta.objects.filter(estado="PENDIENTE", fecha__lte=hace_24h)
            .values("id", "fecha", "total")
            .order_by("fecha")[:10]
        )

        total_alertas = (
            sin_stock.count() + stock_bajo.count() + ventas_pendientes.count()
        )

        return {
            "total": total_alertas,
            "sin_stock": [
                {
                    "producto_id": a["producto__id"],
                    "nombre": a["producto__nombre"],
                    "codigo": a["producto__codigo"],
                    "categoria": a["producto__categoria__nombre"],
                    "tipo": "SIN_STOCK",
                    "severidad": "critica",
                    "mensaje": f"Sin stock: {a['producto__nombre']}",
                }
                for a in sin_stock
            ],
            "stock_bajo": [
                {
                    "producto_id": a["producto__id"],
                    "nombre": a["producto__nombre"],
                    "codigo": a["producto__codigo"],
                    "stock_actual": a["stock_actual"],
                    "stock_minimo": a["producto__stock_minimo"],
                    "tipo": "STOCK_BAJO",
                    "severidad": "advertencia",
                    "mensaje": f"Stock bajo: {a['producto__nombre']} ({a['stock_actual']} unidades)",
                }
                for a in stock_bajo
            ],
            "ventas_pendientes": [
                {
                    "venta_id": v["id"],
                    "total": float(v["total"] or 0),
                    "fecha": v["fecha"].isoformat(),
                    "tipo": "VENTA_PENDIENTE",
                    "severidad": "informacion",
                    "mensaje": f"Venta #{v['id']} lleva más de 24h pendiente",
                }
                for v in ventas_pendientes
            ],
        }

    # ========================================================================
    # ACTIVIDAD RECIENTE
    # ========================================================================

    @staticmethod
    def obtener_actividad_reciente(limite=10):
        """
        Últimas transacciones (ventas y compras mezcladas, ordenadas por fecha).

        Returns:
            Lista de actividades recientes con tipo, fecha, descripción y monto
        """
        actividades = []

        # Últimas ventas
        ultimas_ventas = Venta.objects.select_related("cliente", "usuario").order_by(
            "-fecha"
        )[:limite]

        for v in ultimas_ventas:
            actividades.append(
                {
                    "tipo": "VENTA",
                    "id": v.id,
                    "descripcion": f"Venta a {v.cliente.nombre}",
                    "usuario": v.usuario.username if v.usuario else "-",
                    "monto": float(v.total),
                    "estado": v.estado,
                    "fecha": v.fecha.isoformat(),
                    "icono": "shopping-cart",
                    "color": "green" if v.estado == "COMPLETADA" else "gray",
                }
            )

        # Últimas compras
        ultimas_compras = Compra.objects.select_related("usuario").order_by("-fecha")[
            :limite
        ]

        for c in ultimas_compras:
            actividades.append(
                {
                    "tipo": "COMPRA",
                    "id": c.id,
                    "descripcion": f"Compra a {c.proveedor}",
                    "usuario": c.usuario.username if c.usuario else "-",
                    "monto": float(c.total),
                    "estado": c.estado,
                    "fecha": c.fecha.isoformat(),
                    "icono": "package",
                    "color": "blue" if c.estado == "RECIBIDA" else "gray",
                }
            )

        # Ordenar por fecha descendente y retornar los N más recientes
        actividades.sort(key=lambda x: x["fecha"], reverse=True)
        return actividades[:limite]
