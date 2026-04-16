# apps/documentos/services/documento_service.py
"""
Servicio central de creación y gestión de documentos ERP.

Responsabilidades:
- Crear documentos a partir de Ventas o Compras confirmadas
- Generar numeración secuencial (delega a NumeracionService)
- Generar hash de integridad (SHA-256)
- Crear snapshot de detalles (líneas del documento)
- Anular documentos con motivo
- Validar con full_clean() antes de persistir

Reglas:
- NUNCA crear Documento directamente desde código externo
- Siempre usar este servicio como punto de entrada
- Todas las operaciones son @transaction.atomic
"""

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.documentos.exceptions import (
    DocumentoAnulacionError,
    DocumentoError,
    DocumentoValidacionError,
    DocumentoYaExisteError,
)
from apps.documentos.models import Documento, DocumentoDetalle
from apps.documentos.services.numeracion_service import NumeracionService

logger = logging.getLogger("documentos")


class DocumentoService:
    """
    Punto único de entrada para operaciones con documentos.
    """

    # ──────────────────────────────────────────────────────────────────────
    # CREACIÓN — VENTAS
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def crear_documento_venta(venta, usuario=None, tipo=None) -> Documento:
        """
        Crea documento a partir de una venta completada.

        Args:
            venta: Instancia de Venta (con .detalles, .cliente, etc.)
            usuario: Usuario que genera el documento (opcional)
            tipo: Tipo de documento. Si None, se determina por tipo_documento de la venta:
                  - "FACTURA" → FACTURA_VENTA
                  - "RECIBO"  → TICKET_POS

        Returns:
            Documento: Instancia creada y persistida

        Raises:
            DocumentoYaExisteError: Si ya existe documento para esta venta
            DocumentoValidacionError: Si full_clean() falla
        """
        # Anti-duplicados (respaldo del UniqueConstraint de BD)
        if Documento.objects.filter(venta=venta).exists():
            logger.warning(f"⚠️ Intento de duplicar documento para venta {venta.id}")
            raise DocumentoYaExisteError(
                f"Ya existe un documento emitido para la venta #{venta.id}."
            )

        # Determinar tipo
        if tipo is None:
            tipo_venta = getattr(venta, "tipo_documento", "FACTURA")
            tipo = (
                Documento.TipoDocumento.TICKET_POS
                if tipo_venta == "RECIBO"
                else Documento.TipoDocumento.FACTURA_VENTA
            )

        # Generar número
        numero, secuencia = NumeracionService.siguiente_numero(tipo)

        # Referencia
        referencia = getattr(venta, "numero_documento", None) or f"VT-{venta.id:05d}"

        # Crear documento
        doc = Documento(
            tipo=tipo,
            numero_interno=numero,
            numero_secuencia=secuencia,
            referencia_operacion=referencia,
            venta=venta,
            subtotal=venta.total,
            impuestos=0,
            total=venta.total,
            usuario=usuario,
        )

        # Validar antes de guardar
        try:
            doc.full_clean()
        except DjangoValidationError as e:
            raise DocumentoValidacionError(
                f"Validación fallida para documento de venta: {e.messages}"
            ) from e

        doc.save()

        # Crear líneas de detalle (snapshot inmutable)
        detalles = venta.detalles.select_related("producto").all()
        lineas = []
        for i, det in enumerate(detalles, start=1):
            lineas.append(
                DocumentoDetalle(
                    documento=doc,
                    orden=i,
                    descripcion=det.producto.nombre,
                    producto_id=det.producto_id,
                    cantidad=det.cantidad,
                    precio_unitario=det.precio_unitario,
                    subtotal=det.subtotal,
                )
            )
        DocumentoDetalle.objects.bulk_create(lineas)

        # Hash de integridad (después de crear líneas)
        doc.generar_hash()

        logger.info(
            f"✅ Documento {numero} creado para venta #{venta.id} "
            f"(hash: {doc.codigo_verificacion})"
        )

        return doc

    @staticmethod
    def obtener_o_crear_desde_venta(venta, usuario=None) -> Documento:
        """
        Retorna el documento asociado a una venta. Si no existe, lo crea.
        Útil para procesos de migración y endpoints legacy.
        """
        doc = Documento.objects.filter(venta=venta).first()
        if doc:
            return doc
        return DocumentoService.crear_documento_venta(venta, usuario)

    # ──────────────────────────────────────────────────────────────────────
    # CREACIÓN — COMPRAS
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def crear_documento_compra(compra, usuario=None) -> Documento:
        """
        Crea documento a partir de una compra confirmada.

        Args:
            compra: Instancia de Compra (con .detalles, .proveedor, etc.)
            usuario: Usuario que genera el documento

        Returns:
            Documento: Instancia creada y persistida

        Raises:
            DocumentoYaExisteError: Si ya existe documento para esta compra
            DocumentoValidacionError: Si full_clean() falla
        """
        if Documento.objects.filter(compra=compra).exists():
            logger.warning(f"⚠️ Intento de duplicar documento para compra {compra.id}")
            raise DocumentoYaExisteError(
                f"Ya existe un documento emitido para la compra #{compra.id}."
            )

        tipo = Documento.TipoDocumento.FACTURA_COMPRA
        numero, secuencia = NumeracionService.siguiente_numero(tipo)

        referencia = getattr(compra, "numero_compra", None) or f"CO-{compra.id:05d}"

        doc = Documento(
            tipo=tipo,
            numero_interno=numero,
            numero_secuencia=secuencia,
            referencia_operacion=referencia,
            compra=compra,
            subtotal=compra.total,
            impuestos=0,
            total=compra.total,
            usuario=usuario,
        )

        try:
            doc.full_clean()
        except DjangoValidationError as e:
            raise DocumentoValidacionError(
                f"Validación fallida para documento de compra: {e.messages}"
            ) from e

        doc.save()

        detalles = compra.detalles.select_related("producto").all()
        lineas = []
        for i, det in enumerate(detalles, start=1):
            lineas.append(
                DocumentoDetalle(
                    documento=doc,
                    orden=i,
                    descripcion=det.producto.nombre,
                    producto_id=det.producto_id,
                    cantidad=det.cantidad,
                    precio_unitario=det.precio_compra,
                    subtotal=det.subtotal,
                )
            )
        DocumentoDetalle.objects.bulk_create(lineas)

        doc.generar_hash()

        logger.info(
            f"✅ Documento {numero} creado para compra #{compra.id} "
            f"(hash: {doc.codigo_verificacion})"
        )

        return doc

    @staticmethod
    def obtener_o_crear_desde_compra(compra, usuario=None) -> Documento:
        """
        Retorna el documento asociado a una compra. Si no existe, lo crea.
        """
        doc = Documento.objects.filter(compra=compra).first()
        if doc:
            return doc
        return DocumentoService.crear_documento_compra(compra, usuario)

    # ──────────────────────────────────────────────────────────────────────
    # ANULACIÓN
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def anular_documento(documento_id: int, motivo: str = "") -> Documento:
        """
        Anula un documento existente.

        Args:
            documento_id: PK del documento
            motivo: Motivo de anulación (obligatorio en producción)

        Returns:
            Documento: Instancia actualizada

        Raises:
            DocumentoAnulacionError: Si ya está anulado
            DocumentoError: Si no se encuentra
        """
        try:
            doc = Documento.objects.select_for_update().get(pk=documento_id)
        except Documento.DoesNotExist:
            raise DocumentoError(f"Documento #{documento_id} no encontrado.")

        if doc.estado == Documento.Estado.ANULADO:
            raise DocumentoAnulacionError(
                f"El documento {doc.numero_interno} ya está anulado."
            )

        doc.estado = Documento.Estado.ANULADO
        doc.notas = f"ANULADO: {motivo}" if motivo else "ANULADO por el sistema"
        doc.save(update_fields=["estado", "notas"])

        logger.info(f"🚫 Documento {doc.numero_interno} anulado. Motivo: {motivo}")

        return doc

    # ──────────────────────────────────────────────────────────────────────
    # CONSULTAS
    # ──────────────────────────────────────────────────────────────────────

    @staticmethod
    def obtener_por_venta(venta_id: int) -> Documento | None:
        """Obtiene el documento asociado a una venta (si existe)."""
        return Documento.objects.filter(venta_id=venta_id).first()

    @staticmethod
    def obtener_por_compra(compra_id: int) -> Documento | None:
        """Obtiene el documento asociado a una compra (si existe)."""
        return Documento.objects.filter(compra_id=compra_id).first()

    @staticmethod
    def verificar_hash(documento_id: int) -> bool:
        """
        Verifica integridad del documento recalculando su hash.

        Returns:
            True si el hash coincide (documento íntegro)
            False si hay discrepancia (posible alteración)
        """
        try:
            doc = Documento.objects.prefetch_related("lineas").get(pk=documento_id)
        except Documento.DoesNotExist:
            return False

        hash_original = doc.hash_verificacion
        doc.generar_hash()
        return doc.hash_verificacion == hash_original
