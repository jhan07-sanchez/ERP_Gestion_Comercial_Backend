# apps/auditorias/utils.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    UTILIDADES DE AUDITORÍA - ERP                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿POR QUÉ ESTE ARCHIVO?
══════════════════════
En lugar de que cada view/service tenga que crear un LogAuditoria manualmente
con 15 campos, proveemos funciones helper que lo simplifican.

PATRÓN DE USO (en cualquier view o service del ERP):
════════════════════════════════════════════════════
    from apps.auditorias.utils import registrar_log

    # Ejemplo: registrar que se creó una venta
    registrar_log(
        usuario=request.user,
        accion='CREAR',
        modulo='VENTAS',
        descripcion=f'Se creó la venta #{venta.id}',
        objeto=venta,          # ← GenericFK automático
        request=request,       # ← IP y user-agent automáticos
        datos_despues={...},   # ← opcional: snapshot del objeto
    )

Autor: Sistema ERP
"""

import logging
import traceback
from typing import Optional, Any, Dict

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

logger = logging.getLogger("auditorias")


def registrar_log(
    accion: str,
    modulo: str,
    descripcion: str,
    usuario=None,
    request=None,
    objeto=None,
    objeto_repr: str = "",
    datos_antes: Optional[Dict] = None,
    datos_despues: Optional[Dict] = None,
    extra: Optional[Dict] = None,
    nivel: str = "INFO",
    exitoso: bool = True,
    duracion_ms: Optional[int] = None,
) -> Optional[Any]:
    """
    Función principal para registrar un log de auditoría.

    PARÁMETROS:
    ───────────
    accion       → AccionAuditoria.CREAR / 'CREAR' / etc.
    modulo       → ModuloERP.VENTAS / 'VENTAS' / etc.
    descripcion  → Texto descriptivo de lo que pasó
    usuario      → Instancia del modelo Usuario (o None para sistema)
    request      → HttpRequest de DRF (para extraer IP, user-agent, endpoint)
    objeto       → Instancia del modelo afectado (Venta, Compra, Producto...)
    objeto_repr  → Texto para identificar el objeto (si no se puede inferir)
    datos_antes  → Dict con el estado anterior del objeto (para ediciones)
    datos_despues→ Dict con el nuevo estado del objeto
    extra        → Dict con cualquier dato adicional
    nivel        → 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
    exitoso      → True si la acción fue exitosa, False si falló
    duracion_ms  → Tiempo de respuesta en milisegundos

    RETORNA:
    ────────
    La instancia de LogAuditoria creada, o None si hubo error al guardar
    (nunca levanta excepción para no interrumpir el flujo principal).

    EJEMPLO:
    ────────
    >>> registrar_log(
    ...     usuario=request.user,
    ...     accion='CREAR',
    ...     modulo='VENTAS',
    ...     descripcion='Venta #123 creada por $500.000',
    ...     objeto=venta_instance,
    ...     request=request,
    ... )
    """
    # Importamos aquí para evitar importación circular
    from apps.auditorias.models import LogAuditoria

    try:
        # Preparamos los datos del log
        kwargs = {
            "accion": accion,
            "modulo": modulo,
            "descripcion": descripcion,
            "nivel": nivel,
            "exitoso": exitoso,
            "datos_antes": datos_antes,
            "datos_despues": datos_despues,
            "extra": extra,
            "duracion_ms": duracion_ms,
        }

        # ── Usuario ───────────────────────────────────────────────────────
        if usuario and usuario.is_authenticated:
            kwargs["usuario"] = usuario
            kwargs["usuario_nombre"] = usuario.get_full_name() or usuario.username

        # ── Datos del request (IP, user-agent, endpoint) ──────────────────
        if request:
            kwargs["ip_address"] = _obtener_ip(request)
            kwargs["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:500]
            kwargs["endpoint"] = request.path[:255]
            kwargs["metodo_http"] = request.method

        # ── Objeto afectado (GenericFK) ───────────────────────────────────
        if objeto is not None:
            try:
                kwargs["content_type"] = ContentType.objects.get_for_model(objeto)
                kwargs["object_id"] = str(objeto.pk)
                # Representación legible del objeto
                kwargs["objeto_repr"] = objeto_repr or str(objeto)[:255]
            except Exception:
                pass  # Si falla, continuamos sin el objeto

        # ── Crear el log ──────────────────────────────────────────────────
        # Usamos atomic para que si falla el log, no afecte la transacción
        # principal de la app.
        with transaction.atomic():
            log = LogAuditoria.objects.create(**kwargs)
            return log

    except Exception as e:
        # NUNCA interrumpimos el flujo principal por un error de auditoría
        logger.error(
            f"Error al registrar log de auditoría: {e}\n"
            f"Acción: {accion} | Módulo: {modulo}\n"
            f"{traceback.format_exc()}"
        )
        return None


def _obtener_ip(request) -> Optional[str]:
    """
    Obtiene la IP real del cliente considerando proxies y load balancers.

    ¿Por qué es complicado?
    Cuando hay un proxy/nginx delante de Django, request.META['REMOTE_ADDR']
    devuelve la IP del proxy, no del cliente real. La IP real viene en
    el header X-Forwarded-For.
    """
    # X-Forwarded-For puede tener múltiples IPs: "cliente, proxy1, proxy2"
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        # La primera IP es la del cliente real
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    # Validamos que sea una IP válida (máx 45 chars para IPv6)
    if ip and len(ip) <= 45:
        return ip
    return None


def snapshot_objeto(objeto, campos: Optional[list] = None) -> Dict:
    """
    Crea un 'snapshot' (foto) de un objeto Django como diccionario.

    Útil para guardar el estado antes/después de una edición.

    PARÁMETROS:
    ───────────
    objeto  → Instancia del modelo
    campos  → Lista de campos a incluir (None = todos)

    EJEMPLO:
    ────────
    >>> antes = snapshot_objeto(producto)
    >>> producto.precio_venta = 55000
    >>> producto.save()
    >>> despues = snapshot_objeto(producto)
    >>> registrar_log(..., datos_antes=antes, datos_despues=despues)
    """
    if objeto is None:
        return {}

    try:
        from django.forms.models import model_to_dict

        data = model_to_dict(objeto, fields=campos)

        # Convertir valores no serializables a string
        result = {}
        for key, value in data.items():
            if hasattr(value, "pk"):
                # Es un objeto relacionado, guardamos su representación
                result[key] = f"{value} (id={value.pk})"
            elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                # Es un queryset o lista de ManyToMany
                result[key] = [str(v) for v in value]
            else:
                try:
                    # Intentamos serializar directamente
                    import json

                    json.dumps(value)
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = str(value)

        # Siempre incluimos el ID y repr
        result["id"] = objeto.pk
        result["_repr"] = str(objeto)

        return result
    except Exception as e:
        logger.warning(f"No se pudo hacer snapshot del objeto {objeto}: {e}")
        return {"id": getattr(objeto, "pk", None), "_repr": str(objeto)}


# ============================================================================
# DECORADOR para auditar vistas automáticamente (opcional)
# ============================================================================


def auditar(accion: str, modulo: str, descripcion_tpl: str = ""):
    """
    Decorador que registra automáticamente un log al ejecutar una función.

    CONCEPTOS:
    ──────────
    Un decorador en Python es una función que envuelve otra función
    para agregar comportamiento antes o después.

    USO EN VIEWS:
    ─────────────
    @auditar(accion='EXPORTAR', modulo='VENTAS')
    def exportar_ventas(self, request):
        ...

    PARÁMETROS:
    ───────────
    accion           → Acción a registrar
    modulo           → Módulo del ERP
    descripcion_tpl  → Plantilla de descripción (puede tener {result})
    """
    import functools

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time

            inicio = time.time()

            # Extraer request del primer argumento (self) en ViewSets
            request = None
            usuario = None
            if len(args) >= 2:
                request = getattr(args[1], "META", None) and args[1]
                if request:
                    usuario = getattr(request, "user", None)

            exitoso = True
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                exitoso = False
                raise
            finally:
                duracion = int((time.time() - inicio) * 1000)
                registrar_log(
                    usuario=usuario,
                    request=request,
                    accion=accion,
                    modulo=modulo,
                    descripcion=descripcion_tpl or f"Acción {accion} en {modulo}",
                    nivel="ERROR" if not exitoso else "INFO",
                    exitoso=exitoso,
                    duracion_ms=duracion,
                )

        return wrapper

    return decorator
