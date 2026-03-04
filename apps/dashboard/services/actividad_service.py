from apps.auditorias.services.auditoria_service import AuditoriaService
from django.utils import timezone


class ActividadService:
    @staticmethod
    def registrar(tipo, accion, descripcion, usuario=None, estado="INFO"):
        """
        Registra una actividad en el sistema ERP (Redirigido a Auditoría)
        """
        return AuditoriaService.registrar_accion(
            usuario=usuario,
            accion='ACTUALIZAR', # Mapeo genérico
            modulo='SISTEMA',
            descripcion=f"[{tipo}] {accion}: {descripcion}",
            nivel=estado if estado in ['INFO', 'WARNING', 'ERROR', 'CRITICAL'] else 'INFO'
        )
