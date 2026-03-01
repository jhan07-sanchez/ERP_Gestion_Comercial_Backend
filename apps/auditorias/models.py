# apps/auditorias/models.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    MODELOS DE AUDITORÍA - ERP                              ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿QUÉ ES ESTE ARCHIVO?
═════════════════════
Define la tabla en PostgreSQL donde se guardan TODOS los logs del sistema ERP.
Cada vez que alguien:
  - Inicia sesión / cierra sesión
  - Crea, edita o elimina un registro (venta, compra, producto, etc.)
  - Hace una acción especial (anular venta, ajustar stock, etc.)
  - Tiene un error de seguridad

...queda registrado aquí con todos los detalles.

CONCEPTOS CLAVE DE DJANGO QUE USAMOS AQUÍ:
══════════════════════════════════════════

1. models.Model → clase base de todos los modelos Django
2. ForeignKey    → relación "muchos a uno" (muchos logs → un usuario)
3. CharField     → campo de texto con longitud máxima
4. TextField     → texto largo sin límite
5. JSONField     → almacena diccionarios Python como JSON en PostgreSQL
6. GenericForeignKey → permite apuntar a CUALQUIER modelo (polimorfismo)
   - Esto es clave: un log puede apuntar a una Venta, Compra, Producto, etc.
7. Meta.indexes  → crea índices en PostgreSQL para búsquedas rápidas

Autor: Sistema ERP
"""

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.conf import settings


# ============================================================================
# CONSTANTES - Tipos de Acciones
# ============================================================================


class AccionAuditoria(models.TextChoices):
    """
    Tipos de acciones que se pueden auditar.

    TextChoices es una clase de Django que crea un enum de strings.
    Cada opción tiene: (valor_en_db, etiqueta_legible)

    Uso:
        log.accion = AccionAuditoria.CREAR
        log.get_accion_display()  → "Crear"
    """

    # Autenticación
    LOGIN = "LOGIN", "Inicio de sesión"
    LOGOUT = "LOGOUT", "Cierre de sesión"
    LOGIN_FALLIDO = "LOGIN_FALLIDO", "Intento de login fallido"

    # CRUD básico
    CREAR = "CREAR", "Crear"
    LEER = "LEER", "Consultar"
    ACTUALIZAR = "ACTUALIZAR", "Actualizar"
    ELIMINAR = "ELIMINAR", "Eliminar"

    # Acciones especiales del ERP
    COMPLETAR = "COMPLETAR", "Completar"
    CANCELAR = "CANCELAR", "Cancelar"
    ANULAR = "ANULAR", "Anular"
    APROBAR = "APROBAR", "Aprobar"
    RECHAZAR = "RECHAZAR", "Rechazar"
    AJUSTAR_STOCK = "AJUSTAR_STOCK", "Ajustar Stock"
    EXPORTAR = "EXPORTAR", "Exportar"
    IMPRIMIR = "IMPRIMIR", "Imprimir/Generar PDF"

    # Seguridad
    ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado"
    CAMBIO_CLAVE = "CAMBIO_CLAVE", "Cambio de contraseña"

    # Sistema
    ERROR = "ERROR", "Error del sistema"


class ModuloERP(models.TextChoices):
    """
    Módulos del sistema ERP que pueden generar logs.
    Esto permite filtrar logs por módulo fácilmente.
    """

    USUARIOS = "USUARIOS", "Usuarios"
    CLIENTES = "CLIENTES", "Clientes"
    PROVEEDORES = "PROVEEDORES", "Proveedores"
    INVENTARIO = "INVENTARIO", "Inventario"
    VENTAS = "VENTAS", "Ventas"
    COMPRAS = "COMPRAS", "Compras"
    CAJA = "CAJA", "Caja"
    DOCUMENTOS = "DOCUMENTOS", "Documentos"
    CONFIGURACION = "CONFIGURACION", "Configuración"
    DASHBOARD = "DASHBOARD", "Dashboard"
    SISTEMA = "SISTEMA", "Sistema"


class NivelLog(models.TextChoices):
    """
    Nivel de severidad del log.
    Igual que los niveles de Python logging: DEBUG, INFO, WARNING, ERROR, CRITICAL
    """

    INFO = "INFO", "Información"
    WARNING = "WARNING", "Advertencia"
    ERROR = "ERROR", "Error"
    CRITICAL = "CRITICAL", "Crítico"


# ============================================================================
# MODELO PRINCIPAL
# ============================================================================


class LogAuditoria(models.Model):
    """
    Tabla principal de auditoría del ERP.

    Registra CADA acción importante del sistema.

    ┌─────────────────────────────────────────────────────────────────┐
    │ CAMPOS PRINCIPALES:                                             │
    │                                                                 │
    │ ¿QUIÉN?     → usuario (ForeignKey a Usuario)                   │
    │ ¿QUÉ?       → accion + modulo + descripcion                    │
    │ ¿SOBRE QUÉ? → content_type + object_id (GenericForeignKey)     │
    │ ¿CUÁNDO?    → fecha_hora (auto)                                 │
    │ ¿DESDE DÓNDE? → ip_address + user_agent                        │
    │ ¿CÓMO CAMBIÓ? → datos_antes + datos_despues                    │
    └─────────────────────────────────────────────────────────────────┘
    """

    # ── ¿QUIÉN realizó la acción? ─────────────────────────────────────────
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="logs_auditoria",
        verbose_name="Usuario",
        help_text="Usuario que realizó la acción. NULL si fue el sistema.",
    )

    # Para casos donde el usuario no está autenticado (ej: login fallido)
    usuario_nombre = models.CharField(
        max_length=150,
        blank=True,
        default="",
        verbose_name="Nombre de usuario",
        help_text="Nombre del usuario (guardado para historial aunque se elimine el usuario)",
    )

    # ── ¿QUÉ hizo? ────────────────────────────────────────────────────────
    accion = models.CharField(
        max_length=30,
        choices=AccionAuditoria.choices,
        verbose_name="Acción",
        db_index=True,  # índice para filtrar rápido por acción
        help_text="Tipo de acción realizada",
    )

    modulo = models.CharField(
        max_length=30,
        choices=ModuloERP.choices,
        default=ModuloERP.SISTEMA,
        verbose_name="Módulo",
        db_index=True,
        help_text="Módulo del ERP donde ocurrió la acción",
    )

    nivel = models.CharField(
        max_length=10,
        choices=NivelLog.choices,
        default=NivelLog.INFO,
        verbose_name="Nivel",
        db_index=True,
        help_text="Severidad del log",
    )

    descripcion = models.TextField(
        verbose_name="Descripción",
        help_text="Descripción detallada de la acción realizada",
    )

    # ── ¿SOBRE QUÉ objeto? (GenericForeignKey) ────────────────────────────
    #
    # GenericForeignKey es una técnica avanzada de Django para crear
    # relaciones "polimórficas" — puede apuntar a CUALQUIER modelo.
    #
    # Cómo funciona:
    #   content_type → qué modelo es (ej: "Venta", "Producto", "Cliente")
    #   object_id    → cuál es el ID de ese objeto (ej: 42)
    #   objeto       → acceso directo al objeto (computed, no columna en DB)
    #
    # Ejemplo de uso:
    #   log.content_type = ContentType.objects.get_for_model(Venta)
    #   log.object_id = "42"
    #   log.objeto  → retorna la instancia de Venta con id=42

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tipo de objeto",
        help_text="Modelo afectado (Venta, Compra, Producto, etc.)",
    )
    object_id = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="ID del objeto",
        help_text="ID del registro afectado",
    )
    objeto = GenericForeignKey("content_type", "object_id")

    # Nombre legible del objeto (para mostrar aunque se elimine el objeto)
    objeto_repr = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Descripción del objeto",
        help_text="Representación del objeto al momento del log",
    )

    # ── ¿DESDE DÓNDE? ─────────────────────────────────────────────────────
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
        help_text="IP desde donde se realizó la acción",
    )

    user_agent = models.TextField(
        blank=True,
        default="",
        verbose_name="User Agent",
        help_text="Navegador/cliente HTTP utilizado",
    )

    endpoint = models.CharField(
        max_length=255,
        blank=True,
        default="",
        verbose_name="Endpoint",
        help_text="URL de la API que se llamó",
    )

    metodo_http = models.CharField(
        max_length=10,
        blank=True,
        default="",
        verbose_name="Método HTTP",
        help_text="GET, POST, PUT, PATCH, DELETE",
    )

    # ── ¿CUÁNDO? ──────────────────────────────────────────────────────────
    fecha_hora = models.DateTimeField(
        auto_now_add=True,  # Se establece automáticamente al crear
        verbose_name="Fecha y hora",
        db_index=True,
        help_text="Momento exacto en que ocurrió la acción",
    )

    # ── ¿CÓMO CAMBIÓ el objeto? ───────────────────────────────────────────
    #
    # JSONField almacena un diccionario Python como JSON en PostgreSQL.
    # Ideal para guardar el estado antes/después de una edición.
    #
    # Ejemplo:
    #   datos_antes   = {"precio_venta": 50000, "stock": 100}
    #   datos_despues = {"precio_venta": 55000, "stock": 100}

    datos_antes = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos anteriores",
        help_text="Estado del objeto ANTES de la acción (para ediciones)",
    )

    datos_despues = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos nuevos",
        help_text="Estado del objeto DESPUÉS de la acción",
    )

    # ── Información adicional ─────────────────────────────────────────────
    extra = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Datos extra",
        help_text="Cualquier información adicional en formato JSON",
    )

    exitoso = models.BooleanField(
        default=True,
        verbose_name="Exitoso",
        db_index=True,
        help_text="Indica si la acción fue exitosa o falló",
    )

    duracion_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="Duración (ms)",
        help_text="Tiempo de respuesta en milisegundos",
    )

    # ── Meta ──────────────────────────────────────────────────────────────

    class Meta:
        verbose_name = "Log de Auditoría"
        verbose_name_plural = "Logs de Auditoría"
        ordering = ["-fecha_hora"]  # Más recientes primero

        # Índices para búsquedas rápidas en PostgreSQL
        # Un índice es como el índice de un libro: acelera la búsqueda
        indexes = [
            models.Index(fields=["usuario", "fecha_hora"]),
            models.Index(fields=["modulo", "accion"]),
            models.Index(fields=["modulo", "fecha_hora"]),
            models.Index(fields=["nivel", "fecha_hora"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["ip_address"]),
            models.Index(fields=["exitoso", "fecha_hora"]),
        ]

    def __str__(self):
        return (
            f"[{self.fecha_hora.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"{self.usuario_nombre or 'Sistema'} - "
            f"{self.get_accion_display()} en {self.get_modulo_display()}"
        )

    def save(self, *args, **kwargs):
        """
        Sobrescribimos save() para auto-rellenar campos antes de guardar.

        Esto es un patrón común en Django: ejecutar lógica antes de
        persistir en base de datos.
        """
        # Auto-guardar el nombre del usuario para historial
        if self.usuario and not self.usuario_nombre:
            self.usuario_nombre = self.usuario.get_full_name() or self.usuario.username
        super().save(*args, **kwargs)

    @property
    def tiene_cambios(self):
        """Indica si el log registra cambios en un objeto."""
        return self.datos_antes is not None or self.datos_despues is not None

    @property
    def icono_accion(self):
        """Emoji para representar visualmente la acción."""
        iconos = {
            "LOGIN": "🔑",
            "LOGOUT": "🚪",
            "LOGIN_FALLIDO": "⛔",
            "CREAR": "➕",
            "LEER": "👁️",
            "ACTUALIZAR": "✏️",
            "ELIMINAR": "🗑️",
            "COMPLETAR": "✅",
            "CANCELAR": "❌",
            "ANULAR": "🚫",
            "APROBAR": "✔️",
            "AJUSTAR_STOCK": "📦",
            "EXPORTAR": "📤",
            "IMPRIMIR": "🖨️",
            "ERROR": "💥",
            "ACCESO_DENEGADO": "🔒",
            "CAMBIO_CLAVE": "🔐",
        }
        return iconos.get(self.accion, "📋")
