from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.configuracion.models import ConfiguracionGeneral
from apps.configuracion.services.configuracion_service import ConfiguracionService

@receiver(post_save, sender=ConfiguracionGeneral)
def invalidar_cache_configuracion(sender, instance, **kwargs):
    """
    Invalida el caché de configuración global cuando se detecta un cambio.
    """
    ConfiguracionService.limpiar_cache()
