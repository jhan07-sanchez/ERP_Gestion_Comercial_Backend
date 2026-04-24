# apps/precio/services/precio_service.py
"""
SERVICIO DE LÓGICA DE NEGOCIO — App Precio

¿Qué es un servicio?
─────────────────────
El servicio es la capa donde van las REGLAS DE NEGOCIO complejas.

Regla general en este proyecto:
- Serializer  → valida que los datos sean correctos (tipo, formato)
- Service     → aplica las reglas de negocio (¿qué DEBE pasar?)
- View        → recibe HTTP, llama al service, devuelve respuesta

REGLA DE NEGOCIO PRINCIPAL de este módulo:
──────────────────────────────────────────
Cuando se registra un NUEVO precio vigente para producto+proveedor:
1. El precio ANTERIOR (si existe) debe marcarse como NO vigente (vigente=False)
2. Se le asigna fecha_fin = ahora
3. El nuevo precio queda como vigente=True

Esto preserva el HISTORIAL completo de precios. Nunca se borra nada.

¿Por qué @transaction.atomic?
──────────────────────────────
Cuando hacemos los dos pasos (desactivar viejo + crear nuevo), si falla
el paso 2, queremos que el paso 1 TAMBIÉN se revierta automáticamente.
Esto evita inconsistencias en la base de datos.
transaction.atomic() garantiza que ambas operaciones sean atómicas
(todo o nada).
"""

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Min, Max, Avg, Count
from decimal import Decimal
from typing import Optional, Dict, Any

from apps.precios.models import ListaPrecioCompra
from apps.productos.models import Producto
from apps.proveedores.models import Proveedor

logger = logging.getLogger("precio")


# ============================================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================================


class PrecioError(Exception):
    """Excepción base del módulo precio"""

    pass


class PrecioValidationError(PrecioError):
    """Error de validación de precio"""

    pass


class PrecioStateError(PrecioError):
    """Error de estado (ej: intentar modificar un precio histórico)"""

    pass


# ============================================================================
# SERVICIO PRINCIPAL
# ============================================================================


class ListaPrecioCompraService:
    """
    Servicio para la lógica de negocio de precios de compra.

    Métodos:
    - crear_precio:            Crear nuevo precio (desactivando el anterior)
    - actualizar_precio:       Actualizar campos de un precio
    - desactivar_precio:       Marcar precio como histórico
    - obtener_precio_vigente:  Consultar el precio actual para un par producto+proveedor
    - obtener_historial:       Ver todos los precios históricos
    - obtener_estadisticas:    KPIs del precio (variación, promedio, etc.)
    - comparar_proveedores:    Ver qué proveedor ofrece el menor precio para un producto
    """

    @staticmethod
    @transaction.atomic
    def crear_precio(
        producto: Producto,
        proveedor: Proveedor,
        precio: Decimal,
        fecha_inicio=None,
        usuario=None,
    ) -> ListaPrecioCompra:
        """
        Crear un nuevo precio vigente para un producto+proveedor.

        PROCESO:
        1. Buscar si existe un precio vigente anterior
        2. Si existe: desactivarlo (vigente=False, fecha_fin=ahora)
        3. Crear el nuevo precio (vigente=True)
        4. Retornar el nuevo precio

        Args:
            producto:    Instancia del modelo Producto
            proveedor:   Instancia del modelo Proveedor
            precio:      Decimal con el precio nuevo
            fecha_inicio: Fecha desde la que aplica (default: ahora)
            usuario:     Usuario que registra (para auditoría)

        Returns:
            ListaPrecioCompra: El nuevo precio creado

        Raises:
            PrecioValidationError: Si los datos no son válidos
        """
        ahora = timezone.now()
        fecha_inicio = fecha_inicio or ahora

        logger.info(
            f"🏷️ Creando precio para producto={producto.nombre} "
            f"proveedor={proveedor.nombre} precio=${precio}"
        )

        # ── PASO 1: Buscar precio vigente anterior ─────────────────────────
        precio_anterior = ListaPrecioCompra.objects.filter(
            producto=producto,
            proveedor=proveedor,
            vigente=True,
        ).first()

        # ── PASO 2: Desactivar el precio anterior ──────────────────────────
        if precio_anterior:
            logger.info(f"  → Desactivando precio anterior: ${precio_anterior.precio}")
            precio_anterior.vigente = False
            precio_anterior.fecha_fin = ahora
            precio_anterior.save(update_fields=["vigente", "fecha_fin"])

        # ── PASO 3: Crear el nuevo precio ──────────────────────────────────
        nuevo_precio = ListaPrecioCompra.objects.create(
            producto=producto,
            proveedor=proveedor,
            precio=precio,
            vigente=True,
            fecha_inicio=fecha_inicio,
        )

        logger.info(f"✅ Precio creado exitosamente. ID: {nuevo_precio.id}")

        return nuevo_precio

    @staticmethod
    @transaction.atomic
    def actualizar_precio(
        precio_id: int,
        precio: Optional[Decimal] = None,
        fecha_inicio=None,
        fecha_fin=None,
    ) -> ListaPrecioCompra:
        """
        Actualizar un precio existente.

        Solo se puede modificar un precio VIGENTE.
        Los precios históricos son inmutables (integridad del historial).

        Raises:
            PrecioStateError: Si el precio no está vigente
        """
        try:
            instancia = ListaPrecioCompra.objects.get(id=precio_id)
        except ListaPrecioCompra.DoesNotExist:
            raise PrecioError(f"No existe un precio con ID {precio_id}.")

        if not instancia.vigente:
            raise PrecioStateError(
                "No se puede modificar un precio histórico. "
                "Los precios históricos son inmutables para preservar la integridad del historial."
            )

        if precio is not None:
            instancia.precio = precio
        if fecha_inicio is not None:
            instancia.fecha_inicio = fecha_inicio
        if fecha_fin is not None:
            instancia.fecha_fin = fecha_fin

        instancia.save()
        return instancia

    @staticmethod
    @transaction.atomic
    def desactivar_precio(precio_id: int) -> ListaPrecioCompra:
        """
        Desactivar manualmente un precio (marcarlo como histórico).

        Útil cuando un proveedor deja de ofrecer un producto.

        Raises:
            PrecioStateError: Si ya está desactivado
        """
        try:
            instancia = ListaPrecioCompra.objects.get(id=precio_id)
        except ListaPrecioCompra.DoesNotExist:
            raise PrecioError(f"No existe un precio con ID {precio_id}.")

        if not instancia.vigente:
            raise PrecioStateError("Este precio ya está marcado como histórico.")

        instancia.vigente = False
        instancia.fecha_fin = timezone.now()
        instancia.save(update_fields=["vigente", "fecha_fin"])

        logger.info(
            f"🔕 Precio ID {precio_id} desactivado: "
            f"{instancia.producto.nombre} / {instancia.proveedor.nombre}"
        )

        return instancia

    @staticmethod
    def obtener_precio_vigente(
        producto_id: int,
        proveedor_id: int,
    ) -> Optional[ListaPrecioCompra]:
        """
        Obtener el precio vigente actual para un par producto+proveedor.

        Returns:
            ListaPrecioCompra o None si no hay precio registrado
        """
        return (
            ListaPrecioCompra.objects.filter(
                producto_id=producto_id,
                proveedor_id=proveedor_id,
                vigente=True,
            )
            .select_related("producto", "proveedor")
            .first()
        )

    @staticmethod
    def obtener_historial(
        producto_id: int,
        proveedor_id: int,
    ):
        """
        Obtener el historial completo de precios para un par producto+proveedor.

        Returns:
            QuerySet ordenado del más reciente al más antiguo
        """
        return (
            ListaPrecioCompra.objects.filter(
                producto_id=producto_id,
                proveedor_id=proveedor_id,
            )
            .select_related("producto", "proveedor")
            .order_by("-fecha_inicio")
        )

    @staticmethod
    def obtener_estadisticas_producto(producto_id: int) -> Dict[str, Any]:
        """
        Estadísticas de precios para un producto a lo largo de todos sus proveedores.

        Útil para el responsable de compras: "¿Cuánto nos cuesta este producto?
        ¿Con qué proveedor conviene comprarlo?"

        Returns:
            dict con estadísticas completas
        """
        try:
            producto = Producto.objects.get(id=producto_id)
        except Producto.DoesNotExist:
            raise PrecioError(f"No existe un producto con ID {producto_id}.")

        # Precios vigentes para este producto (todos los proveedores)
        precios_vigentes = ListaPrecioCompra.objects.filter(
            producto=producto,
            vigente=True,
        ).select_related("proveedor")

        # Estadísticas de todos los precios vigentes
        stats = precios_vigentes.aggregate(
            precio_min=Min("precio"),
            precio_max=Max("precio"),
            precio_promedio=Avg("precio"),
            total_proveedores=Count("id"),
        )

        # Proveedor más barato (precio vigente más bajo)
        precio_mas_barato = precios_vigentes.order_by("precio").first()
        # Proveedor más caro
        precio_mas_caro = precios_vigentes.order_by("-precio").first()

        # Total registros históricos
        total_historico = ListaPrecioCompra.objects.filter(producto=producto).count()

        return {
            "producto": {
                "id": producto.id,
                "codigo": producto.codigo,
                "nombre": producto.nombre,
                "precio_venta_actual": float(producto.precio_venta),
            },
            "precios_vigentes": {
                "total_proveedores": stats["total_proveedores"] or 0,
                "precio_minimo": float(stats["precio_min"] or 0),
                "precio_maximo": float(stats["precio_max"] or 0),
                "precio_promedio": float(stats["precio_promedio"] or 0),
                "diferencia_min_max": float(
                    (stats["precio_max"] or 0) - (stats["precio_min"] or 0)
                ),
            },
            "mejor_opcion": {
                "proveedor_id": precio_mas_barato.proveedor.id
                if precio_mas_barato
                else None,
                "proveedor_nombre": precio_mas_barato.proveedor.nombre
                if precio_mas_barato
                else None,
                "precio": float(precio_mas_barato.precio)
                if precio_mas_barato
                else None,
            },
            "peor_opcion": {
                "proveedor_id": precio_mas_caro.proveedor.id
                if precio_mas_caro
                else None,
                "proveedor_nombre": precio_mas_caro.proveedor.nombre
                if precio_mas_caro
                else None,
                "precio": float(precio_mas_caro.precio) if precio_mas_caro else None,
            },
            "historial": {
                "total_registros": total_historico,
            },
            "margen_venta": {
                # Si compramos al precio más bajo, ¿cuánto margen tenemos?
                "con_precio_minimo": float(
                    producto.precio_venta - (stats["precio_min"] or 0)
                ),
                "margen_porcentual": float(
                    (
                        (producto.precio_venta - (stats["precio_min"] or 0))
                        / producto.precio_venta
                        * 100
                    )
                    if producto.precio_venta > 0 and stats["precio_min"]
                    else 0
                ),
            },
        }

    @staticmethod
    def comparar_proveedores(producto_id: int):
        """
        Comparar todos los proveedores vigentes para un producto.

        Returns:
            QuerySet con precios vigentes ordenados del más barato al más caro
        """
        return (
            ListaPrecioCompra.objects.filter(
                producto_id=producto_id,
                vigente=True,
            )
            .select_related("proveedor")
            .order_by("precio")
        )
