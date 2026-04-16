# apps/documentos/services/numeracion_service.py
"""
Servicio de numeración secuencial para documentos ERP.

Características:
- Thread-safe con SELECT FOR UPDATE
- Prefijos configurables por tipo de documento
- Formato: FV-000001, POS-000001, COM-000001
- Retorna tanto el número formateado como el valor numérico (para auditoría)
- Preparado para multi-sucursal (extensible con campo sucursal)
"""

import logging

from django.db import transaction

from apps.documentos.exceptions import NumeracionError
from apps.documentos.models import SecuenciaNumeracionDocumento

logger = logging.getLogger("documentos")


class NumeracionService:
    """
    Genera números de documento secuenciales, thread-safe.

    Usa SELECT FOR UPDATE para garantizar unicidad bajo concurrencia.
    Nunca llamar fuera de un @transaction.atomic.
    """

    PREFIJOS = {
        "FACTURA_VENTA": ("FV", "factura_venta"),
        "TICKET_POS": ("POS", "ticket_pos"),
        "FACTURA_COMPRA": ("COM", "factura_compra"),
    }

    @staticmethod
    @transaction.atomic
    def siguiente_numero(tipo_documento: str) -> tuple[str, int]:
        """
        Genera el siguiente número para el tipo dado.

        Args:
            tipo_documento: Clave de TipoDocumento (FACTURA_VENTA, TICKET_POS, FACTURA_COMPRA)

        Returns:
            tuple: (numero_formateado, valor_secuencia)
                   Ej: ("FV-000001", 1)

        Raises:
            NumeracionError: Si el tipo no es válido o hay error de BD.
        """
        if tipo_documento not in NumeracionService.PREFIJOS:
            raise NumeracionError(
                f"Tipo de documento no válido: '{tipo_documento}'. "
                f"Opciones: {list(NumeracionService.PREFIJOS.keys())}"
            )

        prefijo, codigo = NumeracionService.PREFIJOS[tipo_documento]

        try:
            secuencia, _created = (
                SecuenciaNumeracionDocumento.objects.select_for_update().get_or_create(
                    codigo=codigo,
                    defaults={"prefijo": prefijo, "ultimo_numero": 0},
                )
            )

            secuencia.ultimo_numero += 1
            secuencia.save(update_fields=["ultimo_numero"])

            numero_formateado = f"{prefijo}-{secuencia.ultimo_numero:06d}"

            logger.info(
                f"📄 Numeración generada: {numero_formateado} (secuencia #{secuencia.ultimo_numero})"
            )

            return numero_formateado, secuencia.ultimo_numero

        except Exception as e:
            logger.error(f"❌ Error generando numeración para {tipo_documento}: {e}")
            raise NumeracionError(f"Error generando número de documento: {e}") from e

    @staticmethod
    def obtener_ultimo_numero(tipo_documento: str) -> int:
        """
        Consulta el último número generado sin incrementar.
        Útil para dashboards y auditoría.
        """
        if tipo_documento not in NumeracionService.PREFIJOS:
            return 0

        _, codigo = NumeracionService.PREFIJOS[tipo_documento]

        try:
            secuencia = SecuenciaNumeracionDocumento.objects.get(codigo=codigo)
            return secuencia.ultimo_numero
        except SecuenciaNumeracionDocumento.DoesNotExist:
            return 0
