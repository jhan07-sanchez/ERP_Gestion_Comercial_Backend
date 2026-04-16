"""
Resumen JSON de documento emitido (API read-only, sin acoplar DRF serializers globales).
"""

from __future__ import annotations

import logging
from typing import Any

from apps.documentos.models import Documento

logger = logging.getLogger("documentos")


def _documento_a_dict(doc: Documento) -> dict[str, Any]:
    return {
        "id": doc.id,
        "uuid": str(doc.uuid),
        "codigo_verificacion": doc.codigo_verificacion,
        "tipo": doc.tipo,
        "tipo_display": doc.get_tipo_display(),
        "estado": doc.estado,
        "numero_interno": doc.numero_interno,
        "referencia_operacion": doc.referencia_operacion,
        "subtotal": str(doc.subtotal),
        "impuestos": str(doc.impuestos),
        "total": str(doc.total),
        "fecha_emision": doc.fecha_emision.isoformat() if doc.fecha_emision else None,
        "numero_fiscal": doc.numero_fiscal,
        "prefijo_fiscal": doc.prefijo_fiscal,
    }


def resumen_documento_venta(venta_id: int) -> dict[str, Any] | None:
    try:
        doc = Documento.objects.filter(venta_id=venta_id).first()
        return _documento_a_dict(doc) if doc else None
    except Exception:
        # La tabla aún no existe (migración pendiente) u otro error de BD
        logger.debug("Tabla documentos_documento no disponible aún (¿migración pendiente?).")
        return None


def resumen_documento_compra(compra_id: int) -> dict[str, Any] | None:
    try:
        doc = Documento.objects.filter(compra_id=compra_id).first()
        return _documento_a_dict(doc) if doc else None
    except Exception:
        # La tabla aún no existe (migración pendiente) u otro error de BD
        logger.debug("Tabla documentos_documento no disponible aún (¿migración pendiente?).")
        return None
