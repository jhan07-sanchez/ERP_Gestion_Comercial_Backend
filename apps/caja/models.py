# apps/caja/models.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      MODELOS - MÓDULO CAJA                                 ║
║                                                                              ║
║  Entidades:                                                                  ║
║  - MetodoPago       → Efectivo, Tarjeta, Transferencia, etc.                ║
║  - Caja             → Representa una caja física (o virtual)                 ║
║  - SesionCaja       → Una apertura/cierre de caja por un usuario             ║
║  - MovimientoCaja   → Cada ingreso o egreso dentro de una sesión             ║
║  - ArqueoCaja       → Conteo físico del dinero al momento de arquear         ║
╚══════════════════════════════════════════════════════════════════════════════╝

📚 ¿Por qué esta estructura?

1. MetodoPago: Separar los métodos de pago permite saber cuánto hay en
   efectivo vs cuánto por tarjeta, etc.

2. Caja: Representa una caja física. Puede haber varias en el negocio.
   Esto permite escalar a múltiples puntos de venta.

3. SesionCaja: Es la "apertura" de una caja. Un usuario abre la caja,
   trabaja durante el día, y luego la cierra. Esta es la unidad principal.

4. MovimientoCaja: Cada transacción que afecta el saldo. Puede ser:
   - INGRESO_VENTA: Pago de una venta
   - INGRESO_MANUAL: Ingreso registrado manualmente
   - EGRESO_COMPRA: Pago de una compra
   - EGRESO_GASTO: Un gasto operativo
   - EGRESO_RETIRO: Retiro de dinero de la caja
   - APERTURA: El monto inicial al abrir la caja

5. ArqueoCaja: Es el proceso de "contar" el dinero físicamente y compararlo
   contra lo que el sistema dice que debería haber.
"""

from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


# ============================================================================
# MÉTODO DE PAGO
# ============================================================================


class MetodoPago(models.Model):
    """
    Métodos de pago disponibles en caja.

    Ejemplos:
    - Efectivo
    - Tarjeta débito
    - Tarjeta crédito
    - Transferencia bancaria
    - Nequi / Daviplata
    """

    TIPO_CONTADO = "CONTADO"
    TIPO_CREDITO = "CREDITO"

    TIPO_CHOICES = [
        (TIPO_CONTADO, "Contado"),
        (TIPO_CREDITO, "Crédito"),
    ]

    nombre = models.CharField(
        max_length=50,
        unique=True,
        help_text="Nombre del método de pago (ej: Efectivo, Tarjeta)",
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está activo, aparece como opción al registrar movimientos",
    )
    es_efectivo = models.BooleanField(
        default=False,
        help_text="Marcar si este método cuenta como dinero en efectivo físico",
    )
    #NUEVO CAMPO: tipo de pago (Contado vs Crédito)
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default=TIPO_CONTADO,
        help_text=(
            "CONTADO: requiere saldo en caja y genera egreso inmediato. "
            "CREDITO: no afecta caja y genera una Cuenta por Pagar al proveedor."
        ),
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"

    @property
    def es_contado(self) -> bool:
        return self.tipo == self.TIPO_CONTADO

    @property
    def es_credito(self) -> bool:
        return self.tipo == self.TIPO_CREDITO


# ============================================================================
# CAJA (Punto de venta / caja física)
# ============================================================================


class Caja(models.Model):
    """
    Representa una caja física o punto de venta.

    Permite tener múltiples cajas en el negocio:
    - Caja Principal
    - Caja 2 (sucursal)
    - Caja Online

    💡 Escalabilidad: si el negocio crece, solo se agregan más cajas
    sin cambiar la lógica de negocio.
    """

    nombre = models.CharField(
        max_length=100,
        unique=True,
        help_text="Nombre descriptivo de la caja (ej: Caja Principal)",
    )
    descripcion = models.TextField(
        blank=True, null=True, help_text="Descripción o ubicación de la caja"
    )
    activa = models.BooleanField(
        default=True, help_text="Si la caja está habilitada para operar"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Caja"
        verbose_name_plural = "Cajas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def sesion_activa(self):
        """Retorna la sesión abierta actualmente, o None si no hay ninguna."""
        return self.sesiones.filter(estado="ABIERTA").first()

    @property
    def esta_abierta(self):
        """¿Tiene esta caja una sesión activa ahora mismo?"""
        return self.sesiones.filter(estado="ABIERTA").exists()


# ============================================================================
# SESIÓN DE CAJA (Apertura / Cierre)
# ============================================================================


class SesionCaja(models.Model):
    """
    Una sesión es el período entre la apertura y el cierre de una caja.

    Flujo normal:
    1. Usuario abre la caja → estado = ABIERTA
    2. Se registran movimientos durante el día
    3. Usuario cierra la caja → estado = CERRADA

    Reglas de negocio:
    - Un usuario no puede tener dos sesiones abiertas al mismo tiempo
    - Una caja no puede tener dos sesiones abiertas al mismo tiempo
    - El cierre calcula automáticamente el saldo final
    """

    ESTADO_ABIERTA = "ABIERTA"
    ESTADO_CERRADA = "CERRADA"

    ESTADO_CHOICES = [
        (ESTADO_ABIERTA, "Abierta"),
        (ESTADO_CERRADA, "Cerrada"),
    ]

    caja = models.ForeignKey(
        Caja,
        on_delete=models.PROTECT,
        related_name="sesiones",
        help_text="Caja a la que pertenece esta sesión",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sesiones_caja",
        help_text="Usuario que abrió esta caja",
    )

    # ── Montos ───────────────────────────────────────────────────────────────
    monto_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Dinero con el que se abrió la caja",
    )
    monto_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Saldo calculado al cerrar (sistema)",
    )
    monto_contado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dinero contado físicamente al cerrar",
    )

    # ── Estado y fechas ───────────────────────────────────────────────────────
    estado = models.CharField(
        max_length=10, choices=ESTADO_CHOICES, default=ESTADO_ABIERTA, db_index=True
    )
    fecha_apertura = models.DateTimeField(
        default=timezone.now, help_text="Fecha y hora de apertura"
    )
    fecha_cierre = models.DateTimeField(
        null=True, blank=True, help_text="Fecha y hora de cierre"
    )

    # ── Observaciones ─────────────────────────────────────────────────────────
    observaciones_apertura = models.TextField(
        blank=True, null=True, help_text="Notas al abrir la caja"
    )
    observaciones_cierre = models.TextField(
        blank=True, null=True, help_text="Notas al cerrar la caja"
    )

    class Meta:
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"
        ordering = ["-fecha_apertura"]
        # Índice para búsquedas frecuentes
        indexes = [
            models.Index(fields=["estado", "usuario"]),
            models.Index(fields=["estado", "caja"]),
            models.Index(fields=["fecha_apertura"]),
        ]
        # Constraints de integridad: solo una sesión abierta por caja y por usuario
        constraints = [
            models.UniqueConstraint(
                fields=["caja"],
                condition=models.Q(estado="ABIERTA"),
                name="unique_sesion_abierta_por_caja",
            ),
            models.UniqueConstraint(
                fields=["usuario"],
                condition=models.Q(estado="ABIERTA"),
                name="unique_sesion_abierta_por_usuario",
            ),
        ]

    def __str__(self):
        return f"Sesión {self.caja.nombre} - {self.usuario.username} ({self.fecha_apertura.date()})"

    @property
    def diferencia(self):
        """
        Diferencia entre lo contado y lo esperado.
        Positivo = sobrante, Negativo = faltante
        """
        if self.monto_final is not None and self.monto_contado is not None:
            return self.monto_contado - self.monto_final
        return None

    @property
    def total_ingresos(self):
        """Total de todos los ingresos en esta sesión"""
        resultado = self.movimientos.filter(
            tipo__in=["INGRESO_VENTA", "INGRESO_MANUAL"]
        ).aggregate(total=models.Sum("monto"))
        return resultado["total"] or Decimal("0.00")

    @property
    def total_egresos(self):
        """Total de todos los egresos en esta sesión"""
        resultado = self.movimientos.filter(
            tipo__in=["EGRESO_COMPRA", "EGRESO_GASTO", "EGRESO_RETIRO"]
        ).aggregate(total=models.Sum("monto"))
        return resultado["total"] or Decimal("0.00")

    @property
    def saldo_esperado(self):
        """
        Saldo esperado = monto_inicial + ingresos - egresos
        Este es el valor "teórico" que debería haber en la caja
        """
        return self.monto_inicial + self.total_ingresos - self.total_egresos


# ============================================================================
# MOVIMIENTO DE CAJA
# ============================================================================


class MovimientoCaja(models.Model):
    """
    Registra cada transacción que entra o sale de una sesión de caja.

    Tipos de movimiento:

    INGRESOS:
    - APERTURA      → El monto inicial (se crea automáticamente al abrir)
    - INGRESO_VENTA → Pago recibido por una venta
    - INGRESO_MANUAL → Ingreso registrado manualmente (ej: cobro de deuda)

    EGRESOS:
    - EGRESO_COMPRA  → Pago hecho por una compra a proveedor
    - EGRESO_GASTO   → Gasto operativo (ej: servicio de domicilio, papelería)
    - EGRESO_RETIRO  → Retiro de dinero de la caja

    💡 ¿Por qué separar los tipos?
    Permite hacer reportes específicos: "¿Cuánto ingresó por ventas hoy?"
    vs "¿Cuánto se gastó en gastos operativos?"
    """

    # ── Tipos de movimiento ───────────────────────────────────────────────────
    APERTURA = "APERTURA"
    INGRESO_VENTA = "INGRESO_VENTA"
    INGRESO_MANUAL = "INGRESO_MANUAL"
    EGRESO_COMPRA = "EGRESO_COMPRA"
    EGRESO_GASTO = "EGRESO_GASTO"
    EGRESO_RETIRO = "EGRESO_RETIRO"

    TIPO_CHOICES = [
        # INGRESOS
        (APERTURA, "Apertura de caja"),
        (INGRESO_VENTA, "Ingreso por venta"),
        (INGRESO_MANUAL, "Ingreso manual"),
        # EGRESOS
        (EGRESO_COMPRA, "Egreso por compra"),
        (EGRESO_GASTO, "Egreso por gasto"),
        (EGRESO_RETIRO, "Retiro de dinero"),
    ]

    # Tipos que son INGRESOS (para cálculos)
    TIPOS_INGRESO = [APERTURA, INGRESO_VENTA, INGRESO_MANUAL]
    # Tipos que son EGRESOS
    TIPOS_EGRESO = [EGRESO_COMPRA, EGRESO_GASTO, EGRESO_RETIRO]

    # ── Relaciones ────────────────────────────────────────────────────────────
    sesion = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        related_name="movimientos",
        help_text="Sesión de caja a la que pertenece este movimiento",
    )
    metodo_pago = models.ForeignKey(
        MetodoPago,
        on_delete=models.PROTECT,
        related_name="movimientos",
        help_text="Método de pago utilizado",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="movimientos_caja",
        help_text="Usuario que registró el movimiento",
    )

    # ── Campos del movimiento ─────────────────────────────────────────────────
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        db_index=True,
        help_text="Tipo de movimiento",
    )
    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Valor del movimiento (siempre positivo)",
    )
    descripcion = models.TextField(help_text="Descripción del movimiento")

    # ── Referencias a otros módulos (opcional) ────────────────────────────────
    # Permite vincular el movimiento con una venta o compra específica
    referencia_venta = models.ForeignKey(
        "ventas.Venta",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_caja",
        help_text="Venta asociada a este movimiento (si aplica)",
    )
    referencia_compra = models.ForeignKey(
        "compras.Compra",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movimientos_caja",
        help_text="Compra asociada a este movimiento (si aplica)",
    )

    # ── Auditoría ─────────────────────────────────────────────────────────────
    fecha = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name = "Movimiento de Caja"
        verbose_name_plural = "Movimientos de Caja"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["sesion", "tipo"]),
            models.Index(fields=["tipo", "fecha"]),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - ${self.monto:,.0f}"

    @property
    def es_ingreso(self):
        """¿Este movimiento es un ingreso?"""
        return self.tipo in self.TIPOS_INGRESO

    @property
    def es_egreso(self):
        """¿Este movimiento es un egreso?"""
        return self.tipo in self.TIPOS_EGRESO


# ============================================================================
# ARQUEO DE CAJA
# ============================================================================


class ArqueoCaja(models.Model):
    """
    El arqueo es el proceso de contar físicamente el dinero en caja
    y compararlo con lo que el sistema espera que haya.

    Se puede hacer:
    - Durante la sesión (arqueo parcial): para verificar en medio del día
    - Al cierre: para confirmar el cierre

    El arqueo registra cuántos billetes/monedas hay de cada denominación.
    Esto permite saber exactamente qué hay en la caja.
    """

    TIPO_PARCIAL = "PARCIAL"
    TIPO_CIERRE = "CIERRE"

    TIPO_CHOICES = [
        (TIPO_PARCIAL, "Arqueo parcial"),
        (TIPO_CIERRE, "Arqueo de cierre"),
    ]

    sesion = models.ForeignKey(
        SesionCaja,
        on_delete=models.PROTECT,
        related_name="arqueos",
        help_text="Sesión de caja a la que pertenece este arqueo",
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="arqueos_caja",
        help_text="Usuario que realizó el arqueo",
    )

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default=TIPO_PARCIAL)

    # ── Monto contado ─────────────────────────────────────────────────────────
    monto_contado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total del dinero contado físicamente",
    )
    monto_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Saldo que el sistema esperaba (snapshot al momento del arqueo)",
    )

    # ── Detalle de billetes (JSON) ─────────────────────────────────────────────
    # Formato: {"100000": 3, "50000": 2, "20000": 5, ...}
    # Clave = denominación, Valor = cantidad de billetes/monedas
    detalle_billetes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Detalle del conteo por denominación de billetes",
    )

    # ── Resultado ─────────────────────────────────────────────────────────────
    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Diferencia = monto_contado - monto_esperado",
    )
    observaciones = models.TextField(
        blank=True, null=True, help_text="Notas o justificación de la diferencia"
    )

    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Arqueo de Caja"
        verbose_name_plural = "Arqueos de Caja"
        ordering = ["-fecha"]

    def __str__(self):
        signo = "+" if self.diferencia >= 0 else ""
        return f"Arqueo {self.tipo} - Diferencia: {signo}${self.diferencia:,.0f}"

    def save(self, *args, **kwargs):
        """Calcular la diferencia automáticamente antes de guardar"""
        self.diferencia = self.monto_contado - self.monto_esperado
        super().save(*args, **kwargs)
