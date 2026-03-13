# apps/caja/services/caja_service.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                   SERVICIO DE CAJA - LÓGICA DE NEGOCIO                     ║
╚══════════════════════════════════════════════════════════════════════════════╝

📚 ¿Por qué tener un service?

El SERVICE es la capa donde vive TODA la lógica de negocio.
Los ViewSets solo manejan HTTP (recibir petición → llamar service → devolver respuesta).
Esto hace el código:
- Testeable: puedes testear el service sin HTTP
- Reutilizable: otro módulo puede llamar al service directamente
- Limpio: el ViewSet no tiene lógica mezclada

Patrón:
  ViewSet.create() → valida datos → llama CajaService.abrir_caja() → devuelve resultado
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum
from decimal import Decimal
from typing import Optional, Dict, Any

from apps.caja.services.caja_control import CajaControlService, CajaCerradaOperacionError

from apps.caja.models import (
    Caja,
    SesionCaja,
    MovimientoCaja,
    MetodoPago,
    ArqueoCaja,
)

logger = logging.getLogger("caja")


# ============================================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================================


class CajaError(Exception):
    """Excepción base para errores del módulo caja"""

    pass


class CajaYaAbiertaError(CajaError):
    """Se intenta abrir una caja que ya está abierta"""

    pass


class CajaCerradaError(CajaError):
    """Se intenta operar en una caja cerrada"""

    pass


class SesionNoEncontradaError(CajaError):
    """No se encuentra la sesión solicitada"""

    pass


class MovimientoInvalidoError(CajaError):
    """Los datos del movimiento no son válidos"""

    pass


# ============================================================================
# SERVICIO DE MÉTODOS DE PAGO
# ============================================================================


class MetodoPagoService:
    """Gestión de métodos de pago"""

    @staticmethod
    def crear(nombre: str, es_efectivo: bool = False) -> MetodoPago:
        """Crear un nuevo método de pago"""
        if MetodoPago.objects.filter(nombre=nombre).exists():
            raise CajaError(f'Ya existe un método de pago con el nombre "{nombre}"')
        return MetodoPago.objects.create(nombre=nombre, es_efectivo=es_efectivo)

    @staticmethod
    def activar(metodo_id: int) -> MetodoPago:
        metodo = MetodoPago.objects.get(id=metodo_id)
        metodo.activo = True
        metodo.save()
        return metodo

    @staticmethod
    def desactivar(metodo_id: int) -> MetodoPago:
        metodo = MetodoPago.objects.get(id=metodo_id)
        metodo.activo = False
        metodo.save()
        return metodo


# ============================================================================
# SERVICIO PRINCIPAL DE CAJA
# ============================================================================


class CajaService:
    """
    Servicio central del módulo caja.

    Responsabilidades:
    - Apertura de sesiones
    - Cierre de sesiones
    - Registro de movimientos
    - Arqueos
    - Integración con ventas y compras
    """

    # ── APERTURA ──────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def abrir_caja(
        caja_id: int,
        usuario,
        monto_inicial: Decimal,
        observaciones: Optional[str] = None,
    ) -> SesionCaja:
        """
        Abrir una sesión de caja.

        📚 Proceso:
        1. Validar que la caja existe y está activa
        2. Verificar que NO haya otra sesión abierta (para esta caja O este usuario)
        3. Crear la SesionCaja
        4. Registrar el movimiento de APERTURA automáticamente

        Args:
            caja_id: ID de la caja a abrir
            usuario: Usuario que está abriendo la caja
            monto_inicial: Dinero con el que se abre la caja
            observaciones: Notas opcionales

        Returns:
            SesionCaja: La sesión recién creada

        Raises:
            CajaYaAbiertaError: Si la caja o el usuario ya tienen sesión abierta
        """
        # 1. Obtener la caja
        try:
            caja = Caja.objects.get(id=caja_id)
        except Caja.DoesNotExist:
            raise CajaError(f"No existe una caja con ID {caja_id}")

        if not caja.activa:
            raise CajaError(f'La caja "{caja.nombre}" está desactivada')

        # 2a. Verificar que la CAJA no tenga sesión abierta
        if caja.esta_abierta:
            sesion_actual = caja.sesion_activa
            raise CajaYaAbiertaError(
                f'La caja "{caja.nombre}" ya está abierta por '
                f'"{sesion_actual.usuario.username}" desde '
                f"{sesion_actual.fecha_apertura.strftime('%d/%m/%Y %H:%M')}."
            )

        # 2b. Verificar que el USUARIO no tenga otra sesión abierta
        sesion_usuario = SesionCaja.objects.filter(
            usuario=usuario, estado=SesionCaja.ESTADO_ABIERTA
        ).first()
        if sesion_usuario:
            raise CajaYaAbiertaError(
                f'Ya tienes una caja abierta: "{sesion_usuario.caja.nombre}". '
                f"Debes cerrarla antes de abrir otra."
            )

        # 3. Crear la sesión
        sesion = SesionCaja.objects.create(
            caja=caja,
            usuario=usuario,
            monto_inicial=monto_inicial,
            estado=SesionCaja.ESTADO_ABIERTA,
            observaciones_apertura=observaciones,
        )

        # 4. Registrar movimiento de APERTURA automáticamente
        # Usamos el primer método de pago de tipo efectivo, o el primero disponible
        metodo_efectivo = (
            MetodoPago.objects.filter(activo=True, es_efectivo=True).first()
            or MetodoPago.objects.filter(activo=True).first()
        )

        if metodo_efectivo and monto_inicial > 0:
            MovimientoCaja.objects.create(
                sesion=sesion,
                metodo_pago=metodo_efectivo,
                usuario=usuario,
                tipo=MovimientoCaja.APERTURA,
                monto=monto_inicial,
                descripcion=f"Monto inicial de apertura de caja",
            )

        logger.info(
            f"Caja '{caja.nombre}' abierta por '{usuario.username}' "
            f"con monto inicial ${monto_inicial:,.0f}"
        )

        return sesion

    # ── MOVIMIENTOS ───────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def registrar_movimiento(
        sesion_id: int,
        tipo: str,
        monto: Decimal,
        descripcion: str,
        metodo_pago_id: int,
        usuario,
        referencia_venta_id: Optional[int] = None,
        referencia_compra_id: Optional[int] = None,
    ) -> MovimientoCaja:
        """
        Registrar un movimiento en una sesión de caja.

        📚 Este método es el núcleo: cualquier ingreso o egreso pasa por aquí.

        Args:
            sesion_id: ID de la sesión activa
            tipo: Tipo del movimiento (INGRESO_VENTA, EGRESO_GASTO, etc.)
            monto: Valor del movimiento (siempre positivo)
            descripcion: Texto descriptivo
            metodo_pago_id: ID del método de pago
            usuario: Usuario que registra
            referencia_venta_id: ID de venta asociada (opcional)
            referencia_compra_id: ID de compra asociada (opcional)

        Returns:
            MovimientoCaja: El movimiento creado
        """
        # Validar sesión
        try:
            sesion = SesionCaja.objects.select_related("caja").get(id=sesion_id)
        except SesionCaja.DoesNotExist:
            raise SesionNoEncontradaError(f"No existe sesión con ID {sesion_id}")

        if sesion.estado != SesionCaja.ESTADO_ABIERTA:
            raise CajaCerradaError(
                f"La sesión de caja está {sesion.get_estado_display()}. "
                f"No se pueden registrar movimientos."
            )

        # Validar tipo
        tipos_validos = [
            t[0] for t in MovimientoCaja.TIPO_CHOICES if t[0] != MovimientoCaja.APERTURA
        ]
        if tipo not in tipos_validos:
            raise MovimientoInvalidoError(
                f'Tipo de movimiento "{tipo}" no válido. '
                f"Tipos permitidos: {', '.join(tipos_validos)}"
            )

        # Validar monto
        if monto <= 0:
            raise MovimientoInvalidoError("El monto debe ser mayor a cero")

        # Obtener método de pago
        try:
            metodo_pago = MetodoPago.objects.get(id=metodo_pago_id, activo=True)
        except MetodoPago.DoesNotExist:
            raise MovimientoInvalidoError(
                f"Método de pago ID {metodo_pago_id} no existe o está inactivo"
            )

        # Crear movimiento
        kwargs: Dict[str, Any] = {
            "sesion": sesion,
            "metodo_pago": metodo_pago,
            "usuario": usuario,
            "tipo": tipo,
            "monto": monto,
            "descripcion": descripcion,
        }

        # Vincular con venta si se proporciona
        if referencia_venta_id:
            from apps.ventas.models import Venta

            try:
                kwargs["referencia_venta"] = Venta.objects.get(id=referencia_venta_id)
            except Venta.DoesNotExist:
                raise MovimientoInvalidoError(
                    f"No existe venta con ID {referencia_venta_id}"
                )

        # Vincular con compra si se proporciona
        if referencia_compra_id:
            from apps.compras.models import Compra

            try:
                kwargs["referencia_compra"] = Compra.objects.get(
                    id=referencia_compra_id
                )
            except Compra.DoesNotExist:
                raise MovimientoInvalidoError(
                    f"No existe compra con ID {referencia_compra_id}"
                )

        movimiento = MovimientoCaja.objects.create(**kwargs)

        logger.info(
            f"Movimiento {tipo} de ${monto:,.0f} registrado en sesión {sesion_id} "
            f"por '{usuario.username}'"
        )

        return movimiento

    # ── REGISTRO DESDE VENTAS ─────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def registrar_pago_venta(
        venta,
        usuario,
        metodo_pago_id: int,
        monto: Optional[Decimal] = None,
    ) -> MovimientoCaja:
        """
        Registrar automáticamente el pago de una venta en caja.

        📚 Este método es llamado por el módulo de ventas cuando se completa
        una venta. La integración entre módulos se hace así:
        - El servicio de ventas llama a este método
        - No necesita saber cómo funciona la caja internamente

        REGLA ERP: Requiere caja abierta. Si no hay sesión, lanza excepción.

        Args:
            venta: Instancia del modelo Venta
            usuario: Usuario que registra
            metodo_pago_id: ID del método de pago
            monto: Si None, usa venta.total

        Returns:
            MovimientoCaja: El movimiento de ingreso creado

        Raises:
            CajaCerradaOperacionError: Si no hay caja abierta
        """
        # Verificar caja abierta (lanza excepción si no hay)
        sesion = CajaControlService.verificar_caja_abierta(usuario)

        monto_final = monto if monto is not None else venta.total

        return CajaService.registrar_movimiento(
            sesion_id=sesion.id,
            tipo=MovimientoCaja.INGRESO_VENTA,
            monto=monto_final,
            descripcion=f"Pago de venta #{venta.id}",
            metodo_pago_id=metodo_pago_id,
            usuario=usuario,
            referencia_venta_id=venta.id,
        )

    # ── REGISTRO DESDE COMPRAS ────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def registrar_pago_compra(
        compra,
        usuario,
        metodo_pago_id: int,
        monto: Optional[Decimal] = None,
    ) -> MovimientoCaja:
        """
        Registrar automáticamente el pago de una compra en caja.

        Análogo a registrar_pago_venta pero para egresos.

        REGLA ERP: Requiere caja abierta. Si no hay sesión, lanza excepción.

        Raises:
            CajaCerradaOperacionError: Si no hay caja abierta
        """
        # Verificar caja abierta (lanza excepción si no hay)
        sesion = CajaControlService.verificar_caja_abierta(usuario)

        monto_final = monto if monto is not None else compra.total

        return CajaService.registrar_movimiento(
            sesion_id=sesion.id,
            tipo=MovimientoCaja.EGRESO_COMPRA,
            monto=monto_final,
            descripcion=f"Pago de compra #{compra.id}",
            metodo_pago_id=metodo_pago_id,
            usuario=usuario,
            referencia_compra_id=compra.id,
        )

    # ── ARQUEO ────────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def realizar_arqueo(
        sesion_id: int,
        monto_contado: Decimal,
        usuario,
        tipo: str = ArqueoCaja.TIPO_PARCIAL,
        detalle_billetes: Optional[Dict] = None,
        observaciones: Optional[str] = None,
    ) -> ArqueoCaja:
        """
        Realizar un arqueo de caja.

        📚 El arqueo compara:
        - Lo que el SISTEMA espera (calculado automáticamente)
        - Lo que el usuario CONTÓ físicamente

        La diferencia puede ser:
        - 0: Todo cuadra perfectamente ✅
        - Positivo (+): Hay más dinero del esperado (sobrante)
        - Negativo (-): Hay menos dinero del esperado (faltante)

        Args:
            sesion_id: ID de la sesión activa
            monto_contado: Total del dinero contado físicamente
            usuario: Usuario que realiza el arqueo
            tipo: 'PARCIAL' o 'CIERRE'
            detalle_billetes: Dict con denominaciones y cantidades
            observaciones: Notas sobre la diferencia

        Returns:
            ArqueoCaja: El arqueo creado
        """
        try:
            sesion = SesionCaja.objects.get(id=sesion_id)
        except SesionCaja.DoesNotExist:
            raise SesionNoEncontradaError(f"No existe sesión con ID {sesion_id}")

        if sesion.estado != SesionCaja.ESTADO_ABIERTA:
            raise CajaCerradaError("Solo se puede arquear una sesión abierta")

        # Calcular saldo esperado del sistema
        monto_esperado = sesion.saldo_esperado

        arqueo = ArqueoCaja.objects.create(
            sesion=sesion,
            usuario=usuario,
            tipo=tipo,
            monto_contado=monto_contado,
            monto_esperado=monto_esperado,
            detalle_billetes=detalle_billetes or {},
            observaciones=observaciones,
        )
        # La diferencia se calcula automáticamente en el save() del modelo

        logger.info(
            f"Arqueo {tipo} en sesión {sesion_id}: "
            f"esperado=${monto_esperado:,.0f}, contado=${monto_contado:,.0f}, "
            f"diferencia=${arqueo.diferencia:,.0f}"
        )

        return arqueo

    # ── CIERRE ────────────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def cerrar_caja(
        sesion_id: int,
        usuario,
        monto_contado: Decimal,
        detalle_billetes: Optional[Dict] = None,
        observaciones: Optional[str] = None,
    ) -> SesionCaja:
        """
        Cerrar una sesión de caja.

        📚 Proceso de cierre:
        1. Validar que la sesión existe y está ABIERTA
        2. Calcular el saldo final del sistema
        3. Realizar automáticamente un arqueo de tipo CIERRE
        4. Actualizar la sesión con monto_final y monto_contado
        5. Cambiar estado a CERRADA

        Args:
            sesion_id: ID de la sesión a cerrar
            usuario: Usuario que cierra (debe ser el mismo que abrió, o supervisor)
            monto_contado: Dinero contado al cerrar
            detalle_billetes: Desglose por denominaciones
            observaciones: Notas de cierre

        Returns:
            SesionCaja: La sesión cerrada con todos los datos
        """
        try:
            sesion = SesionCaja.objects.select_related("caja", "usuario").get(
                id=sesion_id
            )
        except SesionCaja.DoesNotExist:
            raise SesionNoEncontradaError(f"No existe sesión con ID {sesion_id}")

        if sesion.estado != SesionCaja.ESTADO_ABIERTA:
            raise CajaCerradaError(f"Esta sesión ya está {sesion.get_estado_display()}")

        # Calcular saldo final del sistema
        monto_final = sesion.saldo_esperado

        # Realizar arqueo de cierre automáticamente
        CajaService.realizar_arqueo(
            sesion_id=sesion_id,
            monto_contado=monto_contado,
            usuario=usuario,
            tipo=ArqueoCaja.TIPO_CIERRE,
            detalle_billetes=detalle_billetes,
            observaciones=observaciones,
        )

        # Cerrar la sesión
        sesion.estado = SesionCaja.ESTADO_CERRADA
        sesion.monto_final = monto_final
        sesion.monto_contado = monto_contado
        sesion.fecha_cierre = timezone.now()
        sesion.observaciones_cierre = observaciones
        sesion.save()

        logger.info(
            f"Caja '{sesion.caja.nombre}' cerrada por '{usuario.username}'. "
            f"Saldo final: ${monto_final:,.0f} | Contado: ${monto_contado:,.0f} | "
            f"Diferencia: ${monto_contado - monto_final:,.0f}"
        )

        return sesion

    # ── ESTADÍSTICAS ──────────────────────────────────────────────────────────

    @staticmethod
    def obtener_resumen_sesion(sesion_id: int) -> Dict[str, Any]:
        """
        Obtener un resumen completo de una sesión de caja.

        Incluye:
        - Montos totales por tipo de movimiento
        - Saldo esperado vs contado
        - Diferencia
        - Historial de arqueos

        Returns:
            dict con el resumen completo
        """
        try:
            sesion = (
                SesionCaja.objects.select_related("caja", "usuario")
                .prefetch_related("movimientos__metodo_pago")
                .get(id=sesion_id)
            )
        except SesionCaja.DoesNotExist:
            raise SesionNoEncontradaError(f"No existe sesión con ID {sesion_id}")

        # Totales por tipo
        movimientos = sesion.movimientos.values("tipo").annotate(total=Sum("monto"))
        totales_por_tipo = {m["tipo"]: float(m["total"]) for m in movimientos}

        # Totales por método de pago
        por_metodo = (
            sesion.movimientos.filter(tipo__in=MovimientoCaja.TIPOS_INGRESO)
            .values("metodo_pago__nombre")
            .annotate(total=Sum("monto"))
        )

        return {
            "sesion_id": sesion.id,
            "caja": sesion.caja.nombre,
            "usuario": sesion.usuario.username,
            "estado": sesion.estado,
            "fecha_apertura": sesion.fecha_apertura,
            "fecha_cierre": sesion.fecha_cierre,
            "monto_inicial": float(sesion.monto_inicial),
            "total_ingresos": float(sesion.total_ingresos),
            "total_egresos": float(sesion.total_egresos),
            "saldo_esperado": float(sesion.saldo_esperado),
            "monto_contado": float(sesion.monto_contado)
            if sesion.monto_contado
            else None,
            "diferencia": float(sesion.diferencia)
            if sesion.diferencia is not None
            else None,
            "totales_por_tipo": totales_por_tipo,
            "ingresos_por_metodo": list(por_metodo),
            "total_movimientos": sesion.movimientos.count(),
        }
