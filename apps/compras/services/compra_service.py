# apps/compras/services/compra_service.py
"""
🔹 SERVICIOS DE LÓGICA DE NEGOCIO - Versión Mejorada
=====================================================

Características:
- Transacciones atómicas
- Logging detallado
- Validaciones de negocio
- Manejo robusto de errores
- Reversión automática en caso de fallo

Autor: Sistema ERP
Versión: 2.0
Fecha: 2026-02-15
"""
from apps.auditorias.services.auditoria_service import AuditoriaService
from datetime import datetime
import logging
from django.db import transaction
from django.db.models import Sum, Count, Avg
from django.utils import timezone
from decimal import Decimal
from typing import Dict, List, Optional

from apps.compras.models import Compra, DetalleCompra, PagoCompra
from apps.productos.models import Producto
from apps.inventario.models import Inventario, MovimientoInventario
from apps.proveedores.models import Proveedor
from apps.caja.services.caja_service import CajaService
from apps.caja.models import MetodoPago

# Configurar logger
logger = logging.getLogger("compras")


# ============================================================================
# EXCEPCIONES PERSONALIZADAS
# ============================================================================


class CompraError(Exception):
    """Excepción base para errores de compras"""

    pass


class CompraValidationError(CompraError):
    """Error de validación de compra"""

    pass


class CompraStateError(CompraError):
    """Error de estado de compra (no se puede realizar la operación)"""

    pass


class InventarioInsuficienteError(CompraError):
    """Error cuando no hay stock suficiente para anular"""

    pass


# ============================================================================
# SERVICIO PRINCIPAL DE COMPRAS
# ============================================================================


class CompraService:
    """
    Servicio para manejar toda la lógica de negocio de Compras

    Métodos:
    - crear_compra: Crear nueva compra
    - actualizar_compra: Actualizar compra existente
    - confirmar_compra: Marcar como REALIZADA y actualizar inventario
    - anular_compra: Anular compra y revertir inventario
    - obtener_estadisticas: Estadísticas de una compra
    - obtener_estadisticas_generales: Estadísticas globales
    """

    # ========================================================================
    # CREAR COMPRA
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def crear_compra(
        proveedor: Proveedor,
        detalles: List[Dict],
        usuario,
        fecha,
        observaciones: Optional[str] = None,
        request=None,
    ) -> Compra:
        """
        Crear una nueva compra con sus detalles

        Args:
            proveedor: Instancia del proveedor
            detalles: Lista de dicts con producto_id, cantidad, precio_compra
            usuario: Usuario que crea la compra
            fecha: Fecha de la compra
            observaciones: Observaciones opcionales

        Returns:
            Compra: Instancia de la compra creada

        Raises:
            CompraValidationError: Si hay errores de validación
            CompraError: Si hay errores generales

        Proceso:
        1. Validar datos
        2. Calcular total
        3. Crear compra (estado PENDIENTE)
        4. Crear detalles
        5. Log de auditoría
        """
        try:
            logger.info(
                f"🆕 Iniciando creación de compra para proveedor {proveedor.nombre}"
            )

            # 1. Validar que hay detalles
            if not detalles or len(detalles) == 0:
                raise CompraValidationError(
                    "Debe incluir al menos un producto en la compra."
                )

            # 2. Validar que el proveedor esté activo
            if not proveedor.estado:
                raise CompraValidationError(
                    f"El proveedor {proveedor.nombre} está inactivo."
                )

            if isinstance(fecha, datetime) is False:
                fecha = timezone.make_aware(
                datetime.combine(fecha, datetime.min.time())
            )
            
            # 3. Calcular el total y validar productos
            total = Decimal("0.00")
            productos_validados = []

            for detalle in detalles:
                producto_id = detalle["producto_id"]
                cantidad = Decimal(str(detalle["cantidad"]))
                precio = detalle.get("precio_compra")

                # Obtener producto
                try:
                    producto = Producto.objects.get(id=producto_id)
                except Producto.DoesNotExist:
                    raise CompraValidationError(
                        f"El producto con ID {producto_id} no existe."
                    )

                # Si no hay precio, usar el del producto
                if precio is None:
                    precio = producto.precio_compra
                else:
                    precio = Decimal(str(precio))

                # Validar precio positivo
                if precio <= 0:
                    raise CompraValidationError(
                        f"El precio del producto '{producto.nombre}' debe ser mayor a 0."
                    )

                subtotal = cantidad * precio
                total += subtotal

                productos_validados.append(
                    {
                        "producto": producto,
                        "cantidad": cantidad,
                        "precio_compra": precio,
                        "subtotal": subtotal,
                    }
                )

            # 4. Crear la compra
            compra = Compra.objects.create(
                proveedor=proveedor,
                usuario=usuario,
                total=total,
                fecha=fecha,
                estado="PENDIENTE",
            )

            # ✅ REGISTRAR AUDITORÍA CORRECTAMENTE
            AuditoriaService.registrar_accion(
                usuario=usuario,
                accion='CREAR',
                modulo='COMPRAS',
                objeto=compra,
                descripcion=f"Compra #{compra.numero_compra} creada",
                request=request,
            )

            # 5. Crear los detalles
            for item in productos_validados:
                DetalleCompra.objects.create(
                    compra=compra,
                    producto=item["producto"],
                    cantidad=item["cantidad"],
                    precio_compra=item["precio_compra"],
                )
            
            logger.info(
                f"✅ Compra {compra.numero_compra} creada exitosamente. "
                f"Total: ${total}, Productos: {len(productos_validados)}"
            )

            return compra

        except CompraValidationError:
            logger.warning(f"⚠️ Error de validación al crear compra")
            raise
        except Exception as e:
            logger.error(f"❌ Error inesperado al crear compra: {str(e)}")
            raise CompraError(f"Error al crear la compra: {str(e)}")

    # ========================================================================
    # REGISTRAR PAGO (PARCIAL O TOTAL)
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def registrar_pago(compra_id, monto, metodo_pago, usuario, referencia=None):
        """
        Registra un pago parcial o total para una compra.
        Actualiza el estado de la compra y aumenta el inventario si es el primer pago.
        """
        try:
            compra = Compra.objects.prefetch_related('detalles__producto').get(id=compra_id)
            
            if compra.estado == 'ANULADA':
                raise CompraStateError('No se pueden registrar pagos a una compra anulada.')
                
            pagos_previos = compra.pagos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            saldo_pendiente = compra.total - Decimal(str(pagos_previos))
            monto_decimal = Decimal(str(monto))
            
            if monto_decimal <= 0:
                raise ValueError('El monto debe ser mayor a 0.')
                
            if monto_decimal > saldo_pendiente:
                raise ValueError(f'El monto excede el saldo pendiente. Saldo actual: {saldo_pendiente}')
            # Mapear el string metodo_pago al modelo MetodoPago de Caja
            # Buscamos de forma case-insensitive, si no existe usamos el primero disponible
            metodo_caja = MetodoPago.objects.filter(nombre__iexact=metodo_pago, activo=True).first()
            if not metodo_caja:
                metodo_caja = MetodoPago.objects.filter(activo=True).first()
                
            if not metodo_caja:
                raise CompraError("No hay métodos de pago activos en Caja para registrar el egreso.")
            
            # 1. Registrar el pago
            pago = PagoCompra.objects.create(
                compra=compra,
                monto=monto_decimal,
                metodo_pago=metodo_pago,
                referencia=referencia,
                usuario=usuario
            )

            # REGLA ERP: Llamar a la caja y registrar el egreso
            # Esto fallará si el usuario no tiene caja abierta (CajaCerradaOperacionError)
            CajaService.registrar_pago_compra(
                compra=compra,
                usuario=usuario,
                metodo_pago_id=metodo_caja.id,
                monto=monto_decimal
            )
            
            # 2. Registrar Auditoría del Pago
            AuditoriaService.registrar_accion(
                usuario=usuario,
                accion='ACTUALIZAR',
                modulo='COMPRAS',
                objeto=compra,
                descripcion=f"Pago de ${monto_decimal} registrado para {compra.numero_compra}",
                request=None
            )
            
            # --- NUEVA LÓGICA DE ACTUALIZACIÓN DE INVENTARIO ---
            # Si se registra un pago (incluso a crédito), evaluamos si ya se entregó el stock
            entradas_existentes = MovimientoInventario.objects.filter(
                referencia__startswith=compra.numero_compra,
                tipo_movimiento="ENTRADA"
            ).exists()

            if not entradas_existentes:
                for detalle in compra.detalles.all():
                    inventario, _ = Inventario.objects.get_or_create(
                        producto=detalle.producto, defaults={"stock_actual": 0}
                    )
                    inventario.stock_actual += detalle.cantidad
                    inventario.save()
                    MovimientoInventario.objects.create(
                        producto=detalle.producto,
                        tipo_movimiento="ENTRADA",
                        cantidad=detalle.cantidad,
                        referencia=f"{compra.numero_compra} - Ingreso por compra (Pago)",
                        usuario=usuario,
                    )
                logger.info(f"📦 Inventario actualizado automáticamente al registrar el primer pago de {compra.numero_compra}")
            # --------------------------------------------------
            
            # 3. Recalcular y actualizar estado de la compra
            nuevo_total_pagado = pagos_previos + monto_decimal
            
            if nuevo_total_pagado >= compra.total:
                compra.estado = 'COMPLETADA'
            else:
                compra.estado = 'PARCIAL'
                
            compra.save()
            
            logger.info(f"✅ Pago de ${monto_decimal} registrado para compra ID: {compra_id}")
            return pago
            
        except Compra.DoesNotExist:
            raise CompraError(f"La compra con ID {compra_id} no existe.")
        except Exception as e:
            logger.error(f"❌ Error al registrar pago para la compra: {str(e)}")
            raise CompraError(f"Error al registrar el pago: {str(e)}")


    # ========================================================================
    # CONFIRMAR COMPRA (SIN PAGO, COMPLETAR MANUALMENTE)
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def confirmar_compra(compra_id: int, usuario) -> Compra:
        """
        Confirmar compra y actualizar inventario

        Args:
            compra_id: ID de la compra
            usuario: Usuario que confirma

        Returns:
            Compra: Compra confirmada

        Raises:
            CompraStateError: Si la compra no está PENDIENTE
            CompraError: Si hay errores generales

        Proceso:
        1. Validar estado PENDIENTE
        2. Aumentar stock de productos
        3. Registrar movimientos de inventario
        4. Cambiar estado a COMPLETADA
        5. Log de auditoría
        """
        try:
            logger.info(f"🔄 Confirmando compra ID: {compra_id}")

            # 1. Obtener compra con detalles
            compra = Compra.objects.prefetch_related("detalles__producto").get(
                id=compra_id
            )

            # 2. Validar estado
            if compra.estado != "PENDIENTE":
                raise CompraStateError(
                    f"Solo se pueden confirmar compras PENDIENTES. "
                    f"Estado actual: {compra.estado}"
                )

            # 3. Actualizar inventario (Solo si NO se ha asignado antes para evitar duplicación)
            # Buscamos si ya existen movimientos de entrada para esta compra
            entradas_existentes = MovimientoInventario.objects.filter(
                referencia__startswith=compra.numero_compra,
                tipo_movimiento="ENTRADA"
            ).exists()

            if not entradas_existentes:
                for detalle in compra.detalles.all():
                    # Obtener o crear inventario
                    inventario, created = Inventario.objects.get_or_create(
                        producto=detalle.producto, defaults={"stock_actual": 0}
                    )
    
                    # Aumentar stock
                    inventario.stock_actual += detalle.cantidad
                    inventario.save()
    
                    # Registrar movimiento
                    MovimientoInventario.objects.create(
                        producto=detalle.producto,
                        tipo_movimiento="ENTRADA",
                        cantidad=detalle.cantidad,
                        referencia=f"{compra.numero_compra} - Confirmación de compra",
                        usuario=usuario,
                    )
    
                    logger.debug(
                        f"  📦 Stock actualizado: {detalle.producto.nombre} "
                        f"+{detalle.cantidad} (Total: {inventario.stock_actual})"
                    )
            else:
                logger.info(f"  ⚠️ El inventario ya había sido actualizado previamente para la compra {compra.numero_compra}")

            # 4. Cambiar estado a COMPLETADA (solo si ya estaba pagada, lo cual es raro al confirmar)
            # Normalmente una compra confirmada pero no pagada sigue PENDIENTE de pago.
            # Sin embargo, para no romper el flujo actual, la dejaremos en PENDIENTE si no hay pagos.
            # Si el usuario quiere que 'Confirmar' no signifique 'Pagado', cambiamos esto:
            # compra.estado = "COMPLETADA" # <-- Esto estaba marcando como pagada sin pagar.
            
            # REGLA ERP: Confirmar = Recibir mercadería. El estado financiero depende de los pagos.
            # Si no hay pagos, el estado debe ser PENDIENTE. Si hay parciales, PARCIAL.
            pagos_totales = compra.pagos.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
            if pagos_totales >= compra.total:
                compra.estado = "COMPLETADA"
            elif pagos_totales > 0:
                compra.estado = "PARCIAL"
            else:
                compra.estado = "PENDIENTE"
                
            compra.save()

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=usuario,
                accion='ACTUALIZAR',
                modulo='COMPRAS',
                objeto=compra,
                descripcion=f"Compra confirmada: {compra.numero_compra}",
                request=None # No hay request en el contexto del servicio directo
            )

            return compra

        except Compra.DoesNotExist:
            raise CompraError(f"La compra con ID {compra_id} no existe.")
        except CompraStateError:
            logger.warning(f"⚠️ Intento de confirmar compra en estado inválido")
            raise
        except Exception as e:
            logger.error(f"❌ Error al confirmar compra: {str(e)}")
            raise CompraError(f"Error al confirmar la compra: {str(e)}")

    # ========================================================================
    # ANULAR COMPRA
    # ========================================================================

    @staticmethod
    @transaction.atomic
    def anular_compra(compra_id: int, usuario, motivo: str) -> Compra:
        """
        Anular compra y revertir inventario si es necesario

        Args:
            compra_id: ID de la compra
            usuario: Usuario que anula
            motivo: Motivo de la anulación

        Returns:
            Compra: Compra anulada

        Raises:
            CompraStateError: Si ya está anulada
            InventarioInsuficienteError: Si no hay stock para revertir
            CompraError: Si hay errores generales

        Proceso:
        1. Validar que NO esté anulada
        2. Si está REALIZADA, validar stock suficiente
        3. Revertir inventario si corresponde
        4. Registrar movimientos de salida
        5. Cambiar estado a ANULADA
        6. Guardar motivo
        7. Log de auditoría
        """
        try:
            logger.info(f"❌ Anulando compra ID: {compra_id}")

            # 1. Obtener compra
            compra = Compra.objects.prefetch_related("detalles__producto").get(
                id=compra_id
            )

            # 2. Validar que no esté anulada
            if compra.estado == "ANULADA":
                raise CompraStateError("La compra ya está anulada.")

            # 3. Revertir inventario solo si se asignó previamente
            entradas_existentes = MovimientoInventario.objects.filter(
                referencia__startswith=compra.numero_compra,
                tipo_movimiento="ENTRADA"
            ).exists()

            if entradas_existentes:
                logger.info(f"  🔄 Revirtiendo inventario para compra {compra.numero_compra}...")

                # Validar stock suficiente para cada producto
                for detalle in compra.detalles.all():
                    try:
                        inventario = Inventario.objects.get(producto=detalle.producto)
                    except Inventario.DoesNotExist:
                        raise InventarioInsuficienteError(
                            f"No existe inventario para el producto "
                            f"'{detalle.producto.nombre}'"
                        )

                    if inventario.stock_actual < detalle.cantidad:
                        raise InventarioInsuficienteError(
                            f"Stock insuficiente para anular. "
                            f"Producto: {detalle.producto.nombre}, "
                            f"Requerido: {detalle.cantidad}, "
                            f"Disponible: {inventario.stock_actual}"
                        )

                # Si llegamos aquí, hay stock suficiente. Revertir.
                for detalle in compra.detalles.all():
                    inventario = Inventario.objects.get(producto=detalle.producto)

                    inventario.stock_actual -= detalle.cantidad
                    inventario.save()

                    # Registrar movimiento de salida
                    MovimientoInventario.objects.create(
                        producto=detalle.producto,
                        tipo_movimiento="SALIDA",
                        cantidad=detalle.cantidad,
                        referencia=(f"{compra.numero_compra} - ANULACIÓN: {motivo}"),
                        usuario=usuario,
                    )

                    logger.debug(
                        f"  📦 Stock revertido: {detalle.producto.nombre} "
                        f"-{detalle.cantidad} (Total: {inventario.stock_actual})"
                    )

            # 5. Cambiar el estado a ANULADA
            compra.estado = "ANULADA"
            compra.motivo_anulacion = motivo
            compra.save()

            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=usuario,
                accion='ELIMINAR', # Usamos ELIMINAR para anulación
                modulo='COMPRAS',
                objeto=compra,
                descripcion=f"Compra anulada: {compra.numero_compra}. Motivo: {motivo}",
                request=None
            )

            return compra

        except Compra.DoesNotExist:
            raise CompraError(f"La compra con ID {compra_id} no existe.")
        except (CompraStateError, InventarioInsuficienteError):
            logger.warning(f"⚠️ Error de estado/inventario al anular compra")
            raise
        except Exception as e:
            logger.error(f"❌ Error al anular compra: {str(e)}")
            raise CompraError(f"Error al anular la compra: {str(e)}")

    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================

    @staticmethod
    def obtener_estadisticas_compra(compra_id: int) -> Dict:
        """
        Obtener estadísticas detalladas de una compra

        Returns:
            dict: Estadísticas completas
        """
        try:
            compra = (
                Compra.objects.select_related("proveedor", "usuario")
                .prefetch_related("detalles__producto")
                .get(id=compra_id)
            )

            # Calcular totales
            total_productos = compra.detalles.count()
            total_unidades = (
                compra.detalles.aggregate(total=Sum("cantidad"))["total"] or 0
            )

            # Calcular margen potencial
            valor_compra = float(compra.total)
            valor_venta_potencial = 0

            for detalle in compra.detalles.all():
                valor_venta_potencial += float(
                    detalle.producto.precio_venta * detalle.cantidad
                )

            ganancia_potencial = valor_venta_potencial - valor_compra
            margen_porcentaje = 0
            if valor_compra > 0:
                margen_porcentaje = (ganancia_potencial / valor_compra) * 100

            return {
                "compra": {
                    "id": compra.id,
                    "numero_compra": compra.numero_compra,
                    "total": valor_compra,
                    "fecha": compra.fecha.isoformat(),
                    "estado": compra.estado,
                },
                "proveedor": {
                    "id": compra.proveedor.id,
                    "nombre": compra.proveedor.nombre,
                    "documento": compra.proveedor.documento,
                },
                "usuario": {
                    "id": compra.usuario.id,
                    "username": compra.usuario.username,
                    "email": compra.usuario.email,
                },
                "productos": {
                    "total_productos": total_productos,
                    "total_unidades": total_unidades,
                },
                "financiero": {
                    "valor_compra": valor_compra,
                    "valor_venta_potencial": valor_venta_potencial,
                    "ganancia_potencial": ganancia_potencial,
                    "margen_porcentaje": round(margen_porcentaje, 2),
                },
            }
        except Compra.DoesNotExist:
            raise CompraError(f"La compra con ID {compra_id} no existe.")

    @staticmethod
    def obtener_estadisticas_generales(
        fecha_inicio: Optional[str] = None, fecha_fin: Optional[str] = None
    ) -> Dict:
        """
        Obtener estadísticas generales de compras

        Args:
            fecha_inicio: Fecha inicial (opcional)
            fecha_fin: Fecha final (opcional)

        Returns:
            dict: Estadísticas globales
        """
        queryset = Compra.objects.all()

        # Filtrar por fechas
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        # Totales generales
        total_compras = queryset.count()
        total_invertido = queryset.aggregate(total=Sum("total"))["total"] or 0
        promedio_compra = queryset.aggregate(promedio=Avg("total"))["promedio"] or 0

        # Por estado
        por_estado = (
            queryset.values("estado")
            .annotate(cantidad=Count("id"), total=Sum("total"))
            .order_by("estado")
        )

        # Top proveedores
        top_proveedores = (
            queryset.values("proveedor__id", "proveedor__nombre")
            .annotate(total_compras=Count("id"), total_invertido=Sum("total"))
            .order_by("-total_invertido")[:10]
        )

        return {
            "periodo": {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin},
            "totales": {
                "total_compras": total_compras,
                "total_invertido": float(total_invertido),
                "promedio_compra": float(promedio_compra),
            },
            "por_estado": list(por_estado),
            "top_proveedores": list(top_proveedores),
            "fecha_consulta": timezone.now().isoformat(),
        }

    @staticmethod
    def obtener_compras_por_proveedor(proveedor_id: int):
        """
        Obtener todas las compras de un proveedor

        Args:
            proveedor_id: ID del proveedor

        Returns:
            QuerySet: Compras del proveedor
        """
        return (
            Compra.objects.filter(proveedor_id=proveedor_id)
            .select_related("usuario", "proveedor")
            .prefetch_related("detalles__producto")
            .order_by("-fecha")
        )
