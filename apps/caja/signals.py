# apps/caja/signals.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                     SEÑALES - MÓDULO CAJA                                  ║
║                                                                              ║
║  Señales para auditoría automática de operaciones de caja.                  ║
║  Registra eventos críticos como apertura, cierre y arqueos.                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.caja.models import SesionCaja, MovimientoCaja, ArqueoCaja, Caja

logger = logging.getLogger("caja.auditoria")


# ============================================================================
# AUDITORÍA DE SESIONES
# ============================================================================


@receiver(post_save, sender=SesionCaja)
def log_sesion_caja(sender, instance, created, **kwargs):
    """
    Registrar en log de auditoría toda apertura y cierre de caja.

    Información registrada:
    - Usuario que abre/cierra
    - Caja utilizada
    - Monto inicial / final
    - Fecha y hora
    """
    if created:
        logger.info(
            f"AUDITORÍA CAJA [APERTURA]: "
            f"usuario='{instance.usuario.username}' "
            f"caja='{instance.caja.nombre}' "
            f"monto_inicial={instance.monto_inicial} "
            f"sesion_id={instance.id}"
        )
    elif instance.estado == SesionCaja.ESTADO_CERRADA and instance.fecha_cierre:
        logger.info(
            f"AUDITORÍA CAJA [CIERRE]: "
            f"usuario='{instance.usuario.username}' "
            f"caja='{instance.caja.nombre}' "
            f"monto_final={instance.monto_final} "
            f"monto_contado={instance.monto_contado} "
            f"sesion_id={instance.id}"
        )


# ============================================================================
# AUDITORÍA DE ARQUEOS
# ============================================================================


@receiver(post_save, sender=ArqueoCaja)
def log_arqueo_caja(sender, instance, created, **kwargs):
    """
    Registrar en log de auditoría los arqueos realizados.
    Especialmente relevante cuando hay diferencia.
    """
    if created:
        nivel = logging.WARNING if instance.diferencia != 0 else logging.INFO
        logger.log(
            nivel,
            f"AUDITORÍA CAJA [ARQUEO]: "
            f"tipo={instance.tipo} "
            f"usuario='{instance.usuario.username}' "
            f"monto_esperado={instance.monto_esperado} "
            f"monto_contado={instance.monto_contado} "
            f"diferencia={instance.diferencia} "
            f"sesion_id={instance.sesion_id}",
        )


# ============================================================================
# PROTECCIÓN DE ELIMINACIÓN
# ============================================================================


@receiver(pre_delete, sender=Caja)
def proteger_eliminacion_caja(sender, instance, **kwargs):
    """
    Impedir la eliminación de una caja que tiene sesiones asociadas.
    Protege la integridad referencial y el historial de auditoría.
    """
    if instance.sesiones.exists():
        from django.db.models import ProtectedError

        raise ProtectedError(
            f'No se puede eliminar la caja "{instance.nombre}" porque tiene '
            f"sesiones asociadas. Desactívela en su lugar.",
            set([instance]),
        )
