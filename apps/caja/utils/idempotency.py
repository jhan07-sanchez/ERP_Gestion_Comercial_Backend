import functools
import logging
from django.core.cache import cache
from rest_framework.response import Response

logger = logging.getLogger("caja")

def require_idempotency_key(view_func):
    """
    Decorador para endpoints que mutan estado financiero.
    Verifica el header 'Idempotency-Key' y evita el doble procesamiento
    respondiendo con la respuesta en caché si la clave ya existe.
    """
    @functools.wraps(view_func)
    def wrapped_view(self, request, *args, **kwargs):
        # 1. Obtener la llave del header
        key = request.headers.get("Idempotency-Key")
        
        # Permitimos paso sin llave para retrocompatibilidad
        # pero para el frontend actual enviaremos el header siempre.
        if not key:
            return view_func(self, request, *args, **kwargs)
            
        cache_key = f"caja_idemp_{key}"
        
        # 2. Check caché
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info("Solicitud idempotente detectada. Devolviendo caché para key: %s", key)
            return Response(cached_data["data"], status=cached_data["status"])
            
        # 3. Procesar petición original
        response = view_func(self, request, *args, **kwargs)
        
        # 4. Guardar en caché si fue un éxito o un error de negocio del usuario (4xx)
        if 200 <= response.status_code < 500:
            # Guardar el data (diccionario) y status (int) para reconstruir la Response
            cache_data = {
                "data": response.data,
                "status": response.status_code
            }
            # Guardamos la llave por 24 horas (86400 segundos)
            cache.set(cache_key, cache_data, 86400)
            
        return response
    return wrapped_view
