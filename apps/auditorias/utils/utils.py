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
    from apps.auditorias.models import LogAuditoria
    try:
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
        if usuario and usuario.is_authenticated:
            kwargs["usuario"] = usuario
            kwargs["usuario_nombre"] = usuario.get_full_name() or usuario.username
        if request:
            kwargs["ip_address"] = _obtener_ip(request)
            kwargs["user_agent"] = request.META.get("HTTP_USER_AGENT", "")[:500]
            kwargs["endpoint"] = request.path[:255]
            kwargs["metodo_http"] = request.method
        if objeto is not None:
            try:
                kwargs["content_type"] = ContentType.objects.get_for_model(objeto)
                kwargs["object_id"] = str(objeto.pk)
                kwargs["objeto_repr"] = objeto_repr or str(objeto)[:255]
            except Exception:
                pass
        with transaction.atomic():
            log = LogAuditoria.objects.create(**kwargs)
            return log
    except Exception as e:
        logger.error(f"Error al registrar log de auditoría: {e}")
        return None

def _obtener_ip(request) -> Optional[str]:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    if ip and len(ip) <= 45:
        return ip
    return None

def snapshot_objeto(objeto, campos: Optional[list] = None) -> Dict:
    if objeto is None: return {}
    try:
        from django.forms.models import model_to_dict
        data = model_to_dict(objeto, fields=campos)
        result = {}
        for key, value in data.items():
            if hasattr(value, "pk"):
                result[key] = f"{value} (id={value.pk})"
            elif hasattr(value, "__iter__") and not isinstance(value, (str, bytes)):
                result[key] = [str(v) for v in value]
            else:
                try:
                    import json
                    json.dumps(value)
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = str(value)
        result["id"] = objeto.pk
        result["_repr"] = str(objeto)
        return result
    except Exception as e:
        return {"id": getattr(objeto, "pk", None), "_repr": str(objeto)}

def auditar(accion: str, modulo: str, descripcion_tpl: str = ""):
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            inicio = time.time()
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
            except Exception:
                exitoso = False
                raise
            finally:
                duracion = int((time.time() - inicio) * 1000)
                registrar_log(
                    usuario=usuario, request=request, accion=accion, modulo=modulo,
                    descripcion=descripcion_tpl or f"Acción {accion} en {modulo}",
                    nivel="ERROR" if not exitoso else "INFO", exitoso=exitoso, duracion_ms=duracion,
                )
        return wrapper
    return decorator
