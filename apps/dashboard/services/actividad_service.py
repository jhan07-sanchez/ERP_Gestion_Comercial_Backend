from apps.dashboard.models import ActividadSistema
from django.utils import timezone


class ActividadService:
    @staticmethod
    def registrar(tipo, accion, descripcion, usuario=None, estado="INFO"):
        """
        Registra una actividad en el sistema ERP
        """

        return ActividadSistema.objects.create(
            tipo=tipo,
            accion=accion,
            descripcion=descripcion,
            usuario=usuario,
            estado=estado,
            fecha=timezone.now(),
        )
