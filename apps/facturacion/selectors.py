from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from apps.facturacion.models import Factura

def obtener_facturas_pendientes_o_vencidas():
    """Retorna facturas con saldo pendiente, ya sean emitidas, parciales o vencidas."""
    return Factura.objects.filter(
        estado__in=["EMITIDA", "PARCIAL", "VENCIDA"]
    ).exclude(saldo_pendiente__lte=0).order_by('fecha_vencimiento')

def obtener_resumen_facturacion_periodo(fecha_inicio, fecha_fin):
    """
    Retorna un resumen de la facturación en un periodo de tiempo.
    """
    facturas = Factura.objects.filter(
        estado__in=["EMITIDA", "PARCIAL", "PAGADA"],
        fecha_emision__range=(fecha_inicio, fecha_fin)
    )
    
    resumen = facturas.aggregate(
        total_facturado=Sum('total'),
        total_pagado=Sum(F('total') - F('saldo_pendiente')),
        saldo_por_cobrar=Sum('saldo_pendiente'),
        cantidad_facturas=Count('id')
    )
    
    # Manejar None cuando no hay facturas
    for key in resumen:
        if resumen[key] is None:
            resumen[key] = 0
            
    return resumen

def obtener_top_clientes(fecha_inicio, fecha_fin, limite=5):
    """
    Retorna los mejores clientes basados en total facturado.
    """
    return Factura.objects.filter(
        estado__in=["EMITIDA", "PARCIAL", "PAGADA"],
        fecha_emision__range=(fecha_inicio, fecha_fin)
    ).values(
        'cliente__id', 'cliente__nombre'
    ).annotate(
        total_comprado=Sum('total')
    ).order_by('-total_comprado')[:limite]

def actualizar_estado_facturas_vencidas():
    """
    Verifica las facturas con saldo y fecha de vencimiento pasada para marcarlas como VENCIDAS.
    Puede ser usado por una tarea programada (Cron).
    """
    hoy = timezone.now().date()
    facturas = Factura.objects.filter(
        estado__in=["EMITIDA", "PARCIAL"],
        fecha_vencimiento__lt=hoy,
        saldo_pendiente__gt=0
    )
    
    count = facturas.update(estado="VENCIDA")
    return count
