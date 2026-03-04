# apps/configuracion/models.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MODELOS - APP CONFIGURACIÓN ERP                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿Qué hace esta app?
-------------------
Gestiona toda la configuración global del sistema ERP:
- Datos de la empresa (nombre, NIT, logo, contacto)
- Configuración fiscal (impuestos, moneda, régimen)
- Numeración de documentos (facturas, compras, recibos)
- Alertas del sistema (stock mínimo global)
- Términos y políticas comerciales

¿Por qué un solo registro?
---------------------------
ConfiguracionGeneral usa el patrón "Singleton":
- Solo existe UN registro en la base de datos
- Se accede siempre con ConfiguracionGeneral.obtener()
- Esto garantiza que toda la app use la misma configuración

Autor: Sistema ERP
Versión: 2.0
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


# ============================================================================
# MODELO PRINCIPAL: CONFIGURACIÓN GENERAL
# ============================================================================


class ConfiguracionGeneral(models.Model):
    """
    Modelo Singleton para la configuración global del ERP.

    ⚠️ IMPORTANTE: Solo debe existir UN registro de este modelo.
    Usar siempre el método .obtener() para acceder a la configuración.

    Patrón Singleton en Django:
    - Se implementa sobrescribiendo save() para evitar múltiples registros
    - El método de clase obtener() crea el registro si no existe (get_or_create)
    """

    # ── Datos de la Empresa ───────────────────────────────────────────────────

    nombre_empresa = models.CharField(
        max_length=150,
        verbose_name="Nombre de la empresa",
        help_text="Nombre comercial que aparecerá en facturas y documentos",
    )

    razon_social = models.CharField(
        max_length=200,
        blank=True,
        default="",
        verbose_name="Razón social",
        help_text="Razón social legal de la empresa",
    )

    nit = models.CharField(
        max_length=50,
        verbose_name="NIT / Documento de identidad",
        help_text="NIT o documento tributario de la empresa",
    )

    telefono = models.CharField(
        max_length=30,
        verbose_name="Teléfono principal",
    )

    telefono_secundario = models.CharField(
        max_length=30,
        blank=True,
        default="",
        verbose_name="Teléfono secundario",
    )

    email = models.EmailField(
        blank=True,
        default="",
        verbose_name="Email de contacto",
    )

    sitio_web = models.URLField(
        blank=True,
        default="",
        verbose_name="Sitio web",
    )

    direccion = models.TextField(
        verbose_name="Dirección",
        help_text="Dirección física de la empresa",
    )

    ciudad = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Ciudad",
    )

    departamento = models.CharField(
        max_length=100,
        blank=True,
        default="",
        verbose_name="Departamento / Estado",
    )

    pais = models.CharField(
        max_length=100,
        default="Colombia",
        verbose_name="País",
    )

    logo = models.ImageField(
        upload_to="configuracion/logos/",
        null=True,
        blank=True,
        verbose_name="Logo de la empresa",
        help_text="Logo que aparecerá en facturas y reportes (PNG o JPG recomendado)",
    )

    # ── Configuración Fiscal ──────────────────────────────────────────────────

    REGIMEN_CHOICES = [
        ("SIMPLIFICADO", "Régimen Simplificado"),
        ("COMUN", "Régimen Común"),
        ("ESPECIAL", "Régimen Especial"),
        ("NO_RESPONSABLE", "No Responsable de IVA"),
    ]

    regimen_fiscal = models.CharField(
        max_length=20,
        choices=REGIMEN_CHOICES,
        default="COMUN",
        verbose_name="Régimen fiscal",
    )

    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=19.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Porcentaje de IVA (%)",
        help_text="Porcentaje de IVA aplicado por defecto (ej: 19.00 para 19%)",
    )

    aplicar_impuesto_por_defecto = models.BooleanField(
        default=True,
        verbose_name="Aplicar IVA por defecto en ventas",
        help_text="Si está activo, el IVA se aplica automáticamente a todos los productos",
    )

    MONEDA_CHOICES = [
        ("COP", "Peso Colombiano (COP)"),
        ("USD", "Dólar Americano (USD)"),
        ("EUR", "Euro (EUR)"),
        ("MXN", "Peso Mexicano (MXN)"),
        ("PEN", "Sol Peruano (PEN)"),
        ("CLP", "Peso Chileno (CLP)"),
        ("ARS", "Peso Argentino (ARS)"),
    ]

    moneda = models.CharField(
        max_length=10,
        choices=MONEDA_CHOICES,
        default="COP",
        verbose_name="Moneda principal",
    )

    simbolo_moneda = models.CharField(
        max_length=5,
        default="$",
        verbose_name="Símbolo de moneda",
        help_text="Símbolo que se muestra antes de los valores (ej: $, €, S/)",
    )

    decimales_precio = models.PositiveSmallIntegerField(
        default=2,
        validators=[MaxValueValidator(4)],
        verbose_name="Decimales en precios",
        help_text="Número de decimales para mostrar precios (0-4)",
    )

    tasa_cambio = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        default=1.0000,
        verbose_name="Tasa de cambio",
        help_text="Tasa de conversión respecto a la moneda base (ej: 1 USD = 4000 COP)",
    )

    # ── Numeración de Documentos ──────────────────────────────────────────────
    # Estos campos controlan el consecutivo automático de cada tipo de documento

    prefijo_factura = models.CharField(
        max_length=10,
        default="FAC",
        verbose_name="Prefijo de factura",
        help_text="Prefijo para el número de factura (ej: FAC → FAC-0001)",
    )

    consecutivo_factura = models.PositiveIntegerField(
        default=1,
        verbose_name="Consecutivo actual de factura",
        help_text="Número desde el cual se generará la próxima factura",
    )

    prefijo_compra = models.CharField(
        max_length=10,
        default="COM",
        verbose_name="Prefijo de compra",
        help_text="Prefijo para el número de compra (ej: COM → COM-0001)",
    )

    consecutivo_compra = models.PositiveIntegerField(
        default=1,
        verbose_name="Consecutivo actual de compra",
    )

    prefijo_recibo = models.CharField(
        max_length=10,
        default="REC",
        verbose_name="Prefijo de recibo POS",
        help_text="Prefijo para recibos de caja/POS",
    )

    consecutivo_recibo = models.PositiveIntegerField(
        default=1,
        verbose_name="Consecutivo actual de recibo",
    )

    digitos_consecutivo = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(3), MaxValueValidator(8)],
        verbose_name="Dígitos del consecutivo",
        help_text="Cantidad de dígitos para rellenar con ceros (ej: 4 → 0001, 6 → 000001)",
    )

    # ── Configuración de Inventario y Alertas ─────────────────────────────────

    stock_minimo_global = models.PositiveIntegerField(
        default=5,
        verbose_name="Stock mínimo global",
        help_text="Stock mínimo por defecto al crear un producto. "
        "Se puede sobreescribir producto por producto.",
    )

    alertar_stock_bajo = models.BooleanField(
        default=True,
        verbose_name="Alertar cuando el stock esté bajo",
        help_text="Mostrar alertas en el dashboard cuando hay productos con stock bajo",
    )

    # ── Configuración de Ventas ───────────────────────────────────────────────

    permitir_descuentos = models.BooleanField(
        default=True,
        verbose_name="Permitir descuentos en ventas",
    )

    descuento_maximo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Descuento máximo permitido (%)",
        help_text="Porcentaje máximo de descuento que puede aplicar un vendedor",
    )

    permitir_venta_sin_stock = models.BooleanField(
        default=False,
        verbose_name="Permitir vender con stock en 0",
        help_text="Si está activo, se pueden hacer ventas aunque no haya stock disponible",
    )

    terminos_condiciones = models.TextField(
        blank=True,
        default="",
        verbose_name="Términos y condiciones",
        help_text="Texto que aparecerá en la parte inferior de las facturas",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────

    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de creación",
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Última actualización",
    )

    # ── Configuración del Modelo ──────────────────────────────────────────────

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuración General"

    def __str__(self):
        return f"Configuración: {self.nombre_empresa}"

    # ── Patrón Singleton ──────────────────────────────────────────────────────

    def save(self, *args, **kwargs):
        """
        Sobrescribimos save() para garantizar que solo exista UN registro.

        ¿Cómo funciona?
        - Si no tiene ID asignado (es un objeto nuevo) y ya existe un registro,
          lanzamos un error de validación.
        - Si ya tiene ID (es una actualización), lo guardamos normalmente.

        Esto es el patrón Singleton en Django.
        """
        if not self.pk and ConfiguracionGeneral.objects.exists():
            raise ValidationError(
                "Solo puede existir una configuración general. "
                "Edite la configuración existente en lugar de crear una nueva."
            )
        super().save(*args, **kwargs)

    @classmethod
    def obtener(cls):
        """
        Método de clase para obtener la configuración.

        ¿Por qué usar esto en lugar de .get() o .first()?
        - get_or_create() crea la configuración con valores por defecto si no existe.
        - Así nunca obtenemos un error "DoesNotExist".
        - Es el punto de acceso único y seguro a la configuración.

        Uso:
            config = ConfiguracionGeneral.obtener()
            print(config.nombre_empresa)
        """
        config, creada = cls.objects.get_or_create(
            pk=1,
            defaults={
                "nombre_empresa": "Mi Empresa",
                "nit": "000000000-0",
                "telefono": "000-0000000",
                "direccion": "Sin dirección configurada",
            },
        )
        return config

    # ── Métodos de utilidad ───────────────────────────────────────────────────

    def generar_numero_factura(self):
        """
        Genera el próximo número de factura y avanza el consecutivo.

        Proceso:
        1. Obtiene el consecutivo actual
        2. Lo formatea con ceros a la izquierda según 'digitos_consecutivo'
        3. Construye el número: PREFIJO-CONSECUTIVO
        4. Incrementa el consecutivo y guarda

        Ejemplo: prefijo="FAC", consecutivo=5, digitos=4 → "FAC-0005"

        ⚠️ IMPORTANTE: Siempre llamar esto dentro de una transacción atómica
        para evitar números duplicados en entornos concurrentes.
        """
        numero = f"{self.prefijo_factura}-{str(self.consecutivo_factura).zfill(self.digitos_consecutivo)}"
        self.consecutivo_factura += 1
        self.save(update_fields=["consecutivo_factura"])
        return numero

    def generar_numero_compra(self):
        """
        Genera el próximo número de compra y avanza el consecutivo.
        Ejemplo: prefijo="COM", consecutivo=3, digitos=4 → "COM-0003"
        """
        numero = f"{self.prefijo_compra}-{str(self.consecutivo_compra).zfill(self.digitos_consecutivo)}"
        self.consecutivo_compra += 1
        self.save(update_fields=["consecutivo_compra"])
        return numero

    def generar_numero_recibo(self):
        """
        Genera el próximo número de recibo POS y avanza el consecutivo.
        Ejemplo: prefijo="REC", consecutivo=12, digitos=4 → "REC-0012"
        """
        numero = f"{self.prefijo_recibo}-{str(self.consecutivo_recibo).zfill(self.digitos_consecutivo)}"
        self.consecutivo_recibo += 1
        self.save(update_fields=["consecutivo_recibo"])
        return numero

    def get_info_empresa(self):
        """
        Retorna un diccionario con la información básica de la empresa.
        Útil para usar en generación de PDFs y reportes.

        Retorna:
            dict: Información estructurada de la empresa
        """
        return {
            "nombre": self.nombre_empresa,
            "razon_social": self.razon_social or self.nombre_empresa,
            "nit": self.nit,
            "telefono": self.telefono,
            "email": self.email,
            "direccion": self.direccion,
            "ciudad": self.ciudad,
            "pais": self.pais,
            "sitio_web": self.sitio_web,
            "logo": self.logo.url if self.logo else None,
            "moneda": self.moneda,
            "simbolo_moneda": self.simbolo_moneda,
            "regimen_fiscal": self.get_regimen_fiscal_display(),
            "terminos": self.terminos_condiciones,
        }
