# apps/caja/services/caja_control.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║               SERVICIO DE CONTROL OPERATIVO DE CAJA                        ║
║                                                                              ║
║  Patrón ERP profesional para control global del estado operativo.            ║
║                                                                              ║
║  REGLA FUNDAMENTAL:                                                          ║
║  CAJA CERRADA = ERP BLOQUEADO OPERATIVAMENTE                                ║
║                                                                              ║
║  Este servicio es consumido por:                                             ║
║  - CajaAbiertaPermission (DRF permission reutilizable)                      ║
║  - @requiere_caja_abierta (decorador)                                       ║
║  - Módulos de ventas, compras, pagos (integración directa)                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import logging
from typing import Optional

from apps.caja.models import SesionCaja

logger = logging.getLogger("caja")


# ============================================================================
# EXCEPCIONES
# ============================================================================


class CajaCerradaOperacionError(Exception):
    """
    Se lanza cuando se intenta realizar una operación financiera
    sin tener una caja abierta.

    Esta excepción es capturada por:
    - CajaAbiertaPermission → retorna HTTP 403
    - Views → retorna HTTP 400 con mensaje claro
    """

    def __init__(self, message=None):
        self.message = message or "Debe abrir una caja antes de realizar operaciones."
        super().__init__(self.message)


# ============================================================================
# SERVICIO CENTRAL DE CONTROL
# ============================================================================


class CajaControlService:
    """
    Servicio central que controla el estado operativo del ERP.

    Responsabilidades:
    - Verificar si un usuario tiene caja abierta
    - Obtener la sesión activa del usuario
    - Lanzar excepciones claras si no hay caja abierta

    Uso típico en otros módulos:

        # En un service de ventas:
        sesion = CajaControlService.verificar_caja_abierta(usuario)

        # En un permission de DRF:
        CajaControlService.tiene_caja_abierta(usuario)

    💡 Un único punto de verificación para todo el ERP.
    """

    @staticmethod
    def obtener_sesion_activa(usuario) -> Optional[SesionCaja]:
        """
        Obtener la sesión de caja abierta del usuario.

        Retorna None si no tiene sesión abierta.
        NO lanza excepción — es una consulta pasiva.

        Args:
            usuario: Instancia del modelo User

        Returns:
            SesionCaja o None
        """
        return (
            SesionCaja.objects.select_related("caja")
            .filter(usuario=usuario, estado=SesionCaja.ESTADO_ABIERTA)
            .first()
        )

    @staticmethod
    def tiene_caja_abierta(usuario) -> bool:
        """
        Verificar si el usuario tiene una caja abierta.

        Retorna True/False — ideal para permissions y checks rápidos.

        Args:
            usuario: Instancia del modelo User

        Returns:
            bool
        """
        return SesionCaja.objects.filter(
            usuario=usuario, estado=SesionCaja.ESTADO_ABIERTA
        ).exists()

    @staticmethod
    def verificar_caja_abierta(usuario) -> SesionCaja:
        """
        Verificar que el usuario tiene caja abierta.
        Si no tiene, lanza CajaCerradaOperacionError.

        Este es el método principal para usar en operaciones financieras.

        Args:
            usuario: Instancia del modelo User

        Returns:
            SesionCaja: La sesión activa del usuario

        Raises:
            CajaCerradaOperacionError: Si no hay caja abierta
        """
        sesion = CajaControlService.obtener_sesion_activa(usuario)

        if not sesion:
            logger.warning(
                f"Operación bloqueada: usuario '{usuario.username}' "
                f"intentó operar sin caja abierta."
            )
            raise CajaCerradaOperacionError()

        return sesion

    @staticmethod
    def verificar_operacion_permitida(usuario) -> SesionCaja:
        """
        Alias semántico de verificar_caja_abierta.

        Uso en otros módulos:
            CajaControlService.verificar_operacion_permitida(request.user)

        Returns:
            SesionCaja: La sesión activa

        Raises:
            CajaCerradaOperacionError
        """
        return CajaControlService.verificar_caja_abierta(usuario)
