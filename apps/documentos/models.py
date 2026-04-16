# apps/documentos/models.py
"""
Modelos del módulo Documentos ERP — Versión Empresarial.

Documento / DocumentoDetalle registran el comprobante fiscal/operativo generado
al completar ventas o al confirmar / completar compras. Desacoplados de la
lógica de inventario y caja; la emisión se orquesta desde servicios dedicados.

Mejoras v2:
- UUID + hash SHA-256 para integridad y verificación
- Código de verificación público (8 chars)
- numero_secuencia auditable
- fecha_vencimiento para créditos
- Índices compuestos para consultas frecuentes
"""

import uuid
import hashlib

from django.conf import settings
from django.db import models


class SecuenciaNumeracionDocumento(models.Model):
    """
    Secuencia simple para numeración interna (preparable para resolución DIAN).

    Cada tipo de documento tiene su propia secuencia:
      - factura_venta  → FV-000001
      - ticket_pos     → POS-000001
      - factura_compra → COM-000001

    Thread-safe: siempre usar select_for_update() al incrementar.
    """

    codigo = models.CharField(max_length=40, unique=True, db_index=True)
    prefijo = models.CharField(max_length=20, default="DOC")
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "documentos_secuencia"
        verbose_name = "Secuencia de documento"
        verbose_name_plural = "Secuencias de documentos"

    def __str__(self):
        return f"{self.codigo} ({self.prefijo}-{self.ultimo_numero:06d})"


class Documento(models.Model):
    """
    Comprobante generado automáticamente desde Venta o Compra.

    Principios:
    - Inmutable una vez emitido (solo se puede ANULAR, nunca editar)
    - Hash SHA-256 garantiza integridad del contenido
    - UUID público para identificación sin exponer PK
    - OneToOneField previene duplicados a nivel de BD
    """

    class TipoDocumento(models.TextChoices):
        FACTURA_VENTA = "FACTURA_VENTA", "Factura de venta"
        TICKET_POS = "TICKET_POS", "Ticket POS"
        FACTURA_COMPRA = "FACTURA_COMPRA", "Factura / documento de compra"

    class Estado(models.TextChoices):
        EMITIDO = "EMITIDO", "Emitido"
        ANULADO = "ANULADO", "Anulado"

    # ── Identificación ────────────────────────────────────────────────────
    uuid = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        null=True,  # Temporal para permitir migración con datos existentes
        db_index=True,
        help_text="Identificador público único (no expone PK).",
    )
    hash_verificacion = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text="SHA-256 del contenido completo para verificación de integridad.",
    )
    codigo_verificacion = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        db_index=True,
        help_text="Código corto alfanumérico de verificación pública.",
    )

    # ── Tipo y estado ─────────────────────────────────────────────────────
    tipo = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        db_index=True,
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.EMITIDO,
        db_index=True,
    )

    # ── Numeración ────────────────────────────────────────────────────────
    numero_interno = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Numeración interna ERP (no fiscal hasta integración DIAN).",
    )
    numero_secuencia = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Valor numérico exacto de la secuencia (para auditoría de huecos).",
    )
    referencia_operacion = models.CharField(
        max_length=50,
        blank=True,
        help_text="Número de venta o compra origen (ej. número factura venta, COMP-xxx).",
    )

    # ── Relaciones (OneToOne = anti-duplicados a nivel BD) ────────────────
    venta = models.OneToOneField(
        "ventas.Venta",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documento_emitido",
    )
    compra = models.OneToOneField(
        "compras.Compra",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="documento_emitido",
    )

    # ── Montos ────────────────────────────────────────────────────────────
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    # ── Campos fiscales (reservados para DIAN / integraciones) ────────────
    numero_fiscal = models.CharField(max_length=50, blank=True, null=True)
    prefijo_fiscal = models.CharField(max_length=20, blank=True, null=True)
    resolucion = models.CharField(max_length=100, blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)

    # ── Fechas ────────────────────────────────────────────────────────────
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento (para ventas a crédito).",
    )

    # ── Auditoría ─────────────────────────────────────────────────────────
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documentos_emitidos",
    )
    notas = models.TextField(
        blank=True,
        null=True,
        help_text="Observaciones o motivo de anulación.",
    )

    class Meta:
        db_table = "documentos_documento"
        ordering = ["-fecha_emision"]
        indexes = [
            models.Index(fields=["tipo", "fecha_emision"]),
            models.Index(fields=["tipo", "numero_interno"], name="idx_tipo_numero"),
        ]

    def __str__(self):
        return f"{self.numero_interno} ({self.get_tipo_display()})"

    # ── Hash de integridad ────────────────────────────────────────────────

    def generar_hash(self):
        """
        Genera SHA-256 basado en datos inmutables del documento + todos sus detalles.

        Incluye:
        - uuid, numero_interno, tipo, total, fecha_emision
        - Cada línea: producto_id, cantidad, precio_unitario, subtotal

        Esto garantiza que cualquier alteración posterior sea detectable.
        """
        # Datos del documento
        partes = [
            str(self.uuid),
            self.numero_interno,
            self.tipo,
            str(self.total),
            str(self.fecha_emision.isoformat()) if self.fecha_emision else "",
        ]

        # Datos de cada línea de detalle (orden determinístico)
        for linea in self.lineas.order_by("orden").all():
            partes.append(
                f"{linea.producto_id or 0}|{linea.cantidad}|{linea.precio_unitario}|{linea.subtotal}"
            )

        cadena = "||".join(partes)
        self.hash_verificacion = hashlib.sha256(cadena.encode("utf-8")).hexdigest()
        self.codigo_verificacion = self.hash_verificacion[:8].upper()
        self.save(update_fields=["hash_verificacion", "codigo_verificacion"])


class DocumentoDetalle(models.Model):
    """Líneas del documento (snapshot de la operación)."""

    documento = models.ForeignKey(
        Documento,
        on_delete=models.CASCADE,
        related_name="lineas",
    )
    orden = models.PositiveSmallIntegerField(default=0)
    descripcion = models.CharField(max_length=300)
    producto_id = models.PositiveIntegerField(null=True, blank=True)
    cantidad = models.DecimalField(max_digits=14, decimal_places=4)
    precio_unitario = models.DecimalField(max_digits=14, decimal_places=4)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "documentos_documento_detalle"
        ordering = ["documento", "orden"]

    def __str__(self):
        return f"{self.documento.numero_interno} — {self.descripcion}"
