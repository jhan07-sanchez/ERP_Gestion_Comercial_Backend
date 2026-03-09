# apps/caja/selectors/caja_selectors.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                        SELECTORS - MÓDULO CAJA                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

📚 ¿Qué son los Selectors?

Los Selectors son funciones o clases que encapsulan las CONSULTAS a la base
de datos. Siguiendo la arquitectura del proyecto:

- Services → Lógica de negocio (crear, modificar, validar)
- Selectors → Consultas y lecturas (buscar, filtrar, listar)

Esta separación tiene ventajas:
1. Las consultas complejas no contaminan los ViewSets
2. Son fáciles de reutilizar en múltiples views
3. Son fáciles de optimizar (agregar .select_related, índices, etc.)
4. Son fáciles de testear

Ejemplo de uso en un ViewSet:
    sesiones = CajaSelector.get_sesiones_usuario(request.user)
    serializer = SesionCajaListSerializer(sesiones, many=True)
"""

from django.db.models import QuerySet, Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Optional

from apps.caja.models import Caja, SesionCaja, MovimientoCaja, ArqueoCaja


# ============================================================================
# SELECTOR DE CAJAS
# ============================================================================


class CajaSelector:
    """Consultas relacionadas con Cajas y Sesiones"""

    @staticmethod
    def get_todas() -> QuerySet:
        """Todas las cajas del sistema"""
        return Caja.objects.all()

    @staticmethod
    def get_activas() -> QuerySet:
        """Solo cajas activas"""
        return Caja.objects.filter(activa=True)

    @staticmethod
    def get_sesion_activa_usuario(usuario) -> Optional[SesionCaja]:
        """
        Obtener la sesión activa del usuario, si tiene una.

        📚 Esto es muy útil para el frontend: al cargar la app de caja,
        el frontend pregunta si el usuario tiene sesión abierta.
        """
        return (
            SesionCaja.objects.select_related("caja", "usuario")
            .filter(usuario=usuario, estado=SesionCaja.ESTADO_ABIERTA)
            .first()
        )

    @staticmethod
    def get_sesiones_filtradas(
        usuario=None,
        caja_id: Optional[int] = None,
        estado: Optional[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
    ) -> QuerySet:
        """
        Obtener sesiones con filtros opcionales.

        Cada parámetro es opcional — si no se pasa, no se aplica ese filtro.
        """
        queryset = SesionCaja.objects.select_related(
            "caja", "usuario"
        ).prefetch_related("movimientos")

        if usuario:
            queryset = queryset.filter(usuario=usuario)
        if caja_id:
            queryset = queryset.filter(caja_id=caja_id)
        if estado:
            queryset = queryset.filter(estado=estado)
        if fecha_inicio:
            queryset = queryset.filter(fecha_apertura__date__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha_apertura__date__lte=fecha_fin)

        return queryset.order_by("-fecha_apertura")

    @staticmethod
    def get_sesion_detail(sesion_id: int) -> Optional[SesionCaja]:
        """Obtener sesión con todos sus relacionados cargados"""
        try:
            return (
                SesionCaja.objects.select_related("caja", "usuario")
                .prefetch_related(
                    "movimientos__metodo_pago",
                    "movimientos__usuario",
                    "movimientos__referencia_venta",
                    "movimientos__referencia_compra",
                    "arqueos__usuario",
                )
                .get(id=sesion_id)
            )
        except SesionCaja.DoesNotExist:
            return None


# ============================================================================
# SELECTOR DE MOVIMIENTOS
# ============================================================================


class MovimientoSelector:
    """Consultas relacionadas con MovimientoCaja"""

    @staticmethod
    def get_movimientos_sesion(
        sesion_id: int,
        tipo: Optional[str] = None,
        metodo_pago_id: Optional[int] = None,
    ) -> QuerySet:
        """
        Obtener movimientos de una sesión, con filtros opcionales.
        """
        queryset = MovimientoCaja.objects.select_related(
            "metodo_pago", "usuario", "referencia_venta", "referencia_compra"
        ).filter(sesion_id=sesion_id)

        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if metodo_pago_id:
            queryset = queryset.filter(metodo_pago_id=metodo_pago_id)

        return queryset.order_by("-fecha")

    @staticmethod
    def get_movimientos_del_dia(usuario=None) -> QuerySet:
        """Movimientos de la sesión activa de hoy"""
        hoy = timezone.now().date()
        queryset = MovimientoCaja.objects.select_related(
            "sesion__caja", "metodo_pago", "usuario"
        ).filter(fecha__date=hoy)

        if usuario:
            queryset = queryset.filter(usuario=usuario)

        return queryset.order_by("-fecha")

    @staticmethod
    def get_resumen_por_tipo(sesion_id: int) -> dict:
        """
        Resumen agrupado por tipo de movimiento para una sesión.

        Útil para mostrar un cuadro resumen en el cierre de caja.
        """
        movimientos = (
            MovimientoCaja.objects.filter(sesion_id=sesion_id)
            .values("tipo")
            .annotate(total=Sum("monto"), cantidad=Count("id"))
            .order_by("tipo")
        )

        return {
            m["tipo"]: {"total": float(m["total"]), "cantidad": m["cantidad"]}
            for m in movimientos
        }

    @staticmethod
    def get_resumen_por_metodo(sesion_id: int) -> list:
        """
        Resumen de ingresos agrupado por método de pago.

        Útil para saber cuánto recibieron en efectivo, tarjeta, etc.
        """
        return list(
            MovimientoCaja.objects.filter(
                sesion_id=sesion_id, tipo__in=MovimientoCaja.TIPOS_INGRESO
            )
            .values("metodo_pago__nombre", "metodo_pago__es_efectivo")
            .annotate(total=Sum("monto"), cantidad=Count("id"))
            .order_by("-total")
        )


# ============================================================================
# SELECTOR DE ESTADÍSTICAS
# ============================================================================


class EstadisticasCajaSelector:
    """Consultas para KPIs y reportes del módulo caja"""

    @staticmethod
    def get_resumen_hoy() -> dict:
        """
        Resumen de todas las cajas en el día de hoy.

        📚 Este selector es útil para el dashboard del ERP:
        muestra cuánto entró y salió de caja hoy.
        """
        hoy = timezone.now().date()

        sesiones_hoy = SesionCaja.objects.filter(fecha_apertura__date=hoy)

        movimientos_hoy = MovimientoCaja.objects.filter(fecha__date=hoy)

        total_ingresos = (
            movimientos_hoy.filter(tipo__in=MovimientoCaja.TIPOS_INGRESO).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        total_egresos = (
            movimientos_hoy.filter(tipo__in=MovimientoCaja.TIPOS_EGRESO).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        return {
            "fecha": hoy,
            "sesiones_abiertas": sesiones_hoy.filter(estado="ABIERTA").count(),
            "sesiones_cerradas": sesiones_hoy.filter(estado="CERRADA").count(),
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "saldo_neto": float(total_ingresos - total_egresos),
        }

    @staticmethod
    def get_resumen_rango(fecha_inicio: str, fecha_fin: str) -> dict:
        """
        Resumen de caja en un rango de fechas.

        Útil para reportes semanales o mensuales.
        """
        movimientos = MovimientoCaja.objects.filter(
            fecha__date__gte=fecha_inicio,
            fecha__date__lte=fecha_fin,
        )

        total_ingresos = (
            movimientos.filter(tipo__in=MovimientoCaja.TIPOS_INGRESO).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        total_egresos = (
            movimientos.filter(tipo__in=MovimientoCaja.TIPOS_EGRESO).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        total_ventas = (
            movimientos.filter(tipo=MovimientoCaja.INGRESO_VENTA).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        total_compras = (
            movimientos.filter(tipo=MovimientoCaja.EGRESO_COMPRA).aggregate(
                total=Sum("monto")
            )["total"]
            or 0
        )

        return {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_ingresos": float(total_ingresos),
            "total_egresos": float(total_egresos),
            "total_ventas": float(total_ventas),
            "total_compras": float(total_compras),
            "saldo_neto": float(total_ingresos - total_egresos),
            "sesiones": SesionCaja.objects.filter(
                fecha_apertura__date__gte=fecha_inicio,
                fecha_apertura__date__lte=fecha_fin,
            ).count(),
        }
