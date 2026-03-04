# apps/configuracion/services.py
"""
Servicios de Lógica de Negocio para Configuración

¿Qué es un servicio y por qué existe?
---------------------------------------
Un servicio es una capa entre las vistas y los modelos.
Contiene la lógica de negocio compleja.

Principio: "Las vistas reciben requests, los servicios hacen el trabajo"

Ventajas:
- Si la lógica cambia, solo modificamos el servicio (no la vista)
- Se puede reutilizar desde múltiples vistas o tareas programadas
- Más fácil de hacer pruebas (tests) unitarios
- El código queda más organizado y legible

Autor: Sistema ERP
"""

from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.cache import cache
from apps.configuracion.models import ConfiguracionGeneral

CACHE_KEY = "global_config_singleton"
CACHE_TIMEOUT = 3600 * 24  # 24 horas


class ConfiguracionService:
    """
    Servicio para manejar la lógica de negocio de la Configuración General.
    Implementa caché para optimizar el rendimiento del ERP.
    """

    @staticmethod
    def limpiar_cache():
        """Elimina la configuración del caché global."""
        cache.delete(CACHE_KEY)

    @staticmethod
    def obtener_configuracion() -> ConfiguracionGeneral:
        """
        Obtiene la configuración general del sistema con soporte de caché.
        """
        config = cache.get(CACHE_KEY)
        if not config:
            config = ConfiguracionGeneral.obtener()
            cache.set(CACHE_KEY, config, CACHE_TIMEOUT)
        return config

    @staticmethod
    def get_valor(campo: str, fallback=None):
        """
        Retorna el valor de un parámetro específico con fallback seguro.
        Útil para consultas rápidas desde otros módulos.
        """
        config = ConfiguracionService.obtener_configuracion()
        return getattr(config, campo, fallback)

    @staticmethod
    @transaction.atomic
    def actualizar_configuracion(datos_validados: dict) -> ConfiguracionGeneral:
        """
        Actualiza la configuración e invalida el caché.
        """
        config = ConfiguracionGeneral.obtener()

        for campo, valor in datos_validados.items():
            setattr(config, campo, valor)

        config.save()
        ConfiguracionService.limpiar_cache()
        return config

    @staticmethod
    @transaction.atomic
    def reset_consecutivo(tipo: str, nuevo_consecutivo: int) -> ConfiguracionGeneral:
        """
        Resetea un consecutivo e invalida el caché.
        """
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)

        campo_mapa = {
            "factura": "consecutivo_factura",
            "compra": "consecutivo_compra",
            "recibo": "consecutivo_recibo",
        }

        if tipo not in campo_mapa:
            raise ValueError(f"Tipo no válido: '{tipo}'")

        campo = campo_mapa[tipo]
        setattr(config, campo, nuevo_consecutivo)
        config.save(update_fields=[campo])

        ConfiguracionService.limpiar_cache()
        return config

    @staticmethod
    def obtener_info_empresa() -> dict:
        """Retorna info básica desde el caché."""
        config = ConfiguracionService.obtener_configuracion()
        return config.get_info_empresa()

    @staticmethod
    def generar_numero_factura() -> str:
        """Genera número y limpia caché para reflejar nuevo consecutivo."""
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        numero = config.generar_numero_factura()
        ConfiguracionService.limpiar_cache()
        return numero

    @staticmethod
    def generar_numero_compra() -> str:
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        numero = config.generar_numero_compra()
        ConfiguracionService.limpiar_cache()
        return numero

    @staticmethod
    def generar_numero_recibo() -> str:
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        numero = config.generar_numero_recibo()
        ConfiguracionService.limpiar_cache()
        return numero
