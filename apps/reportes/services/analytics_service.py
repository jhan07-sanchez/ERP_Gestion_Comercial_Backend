from django.db.models import Sum, Count, F, Q, Avg
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from apps.ventas.models import Venta
from apps.inventario.models import Inventario, MovimientoInventario
from apps.usuarios.models import Usuario

class AnalyticsService:
    """
    Servicio de Inteligencia de Negocios (BI):
    - Eficiencia Operativa
    - Productividad de Equipo
    - Tendencias y Proyecciones
    """

    @staticmethod
    def get_eficiencia_operativa(fecha_inicio=None, fecha_fin=None):
        """
        Cálculo de eficiencia: Rotación de Inventario y Costos vs Ventas
        """
        # ... lógica de eficiencia ...
        # (Reutilizamos y mejoramos la del DashboardService)
        # ...
        return {} # Implementación detallada a seguir

    @staticmethod
    def get_productividad(fecha_inicio=None, fecha_fin=None):
        """
        Análisis de ventas por empleado y rendimiento
        """
        query = Q(estado="COMPLETADA")
        if fecha_inicio: query &= Q(fecha__gte=fecha_inicio)
        if fecha_fin: query &= Q(fecha__lte=fecha_fin)
        
        datos = Venta.objects.filter(query).values(
            "usuario__id", 
            "usuario__first_name", 
            "usuario__last_name"
        ).annotate(
            total_ventas=Sum("total"),
            cantidad=Count("id"),
            ticket_promedio=Avg("total")
        ).order_by("-total_ventas")
        
        return [
            {
                "empleado_id": d["usuario__id"],
                "nombre": f"{d['usuario__first_name']} {d['usuario__last_name']}",
                "total_ventas": float(d["total_ventas"]),
                "cantidad": d["cantidad"],
                "ticket_promedio": float(d["ticket_promedio"])
            }
            for d in datos
        ]

    @staticmethod
    def get_proyecciones_ventas():
        """
        Proyección de ventas futuras usando promedio móvil simple de los últimos 30 días
        """
        hoy = timezone.now().date()
        inicio = hoy - timedelta(days=30)
        
        ventas_30_dias = Venta.objects.filter(
            fecha__date__range=(inicio, hoy),
            estado="COMPLETADA"
        ).annotate(dia=TruncDay("fecha")).values("dia").annotate(total=Sum("total"))
        
        promedio_diario = float(sum(v["total"] for v in ventas_30_dias) / 30 if ventas_30_dias else 0)
        
        # Proyección a 7, 15 y 30 días
        return {
            "diario_promedio": promedio_diario,
            "proyeccion_7d": promedio_diario * 7,
            "proyeccion_15d": promedio_diario * 15,
            "proyeccion_30d": promedio_diario * 30
        }
