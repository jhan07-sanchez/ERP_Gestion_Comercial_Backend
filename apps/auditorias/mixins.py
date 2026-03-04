# apps/auditorias/mixins.py
from typing import Any
from rest_framework import status
from apps.auditorias.services.auditoria_service import AuditoriaService
from apps.auditorias.utils import snapshot_objeto

class MixinAuditable:
    """
    Mixin para ViewSets que registra automáticamente acciones CRUD.
    """
    modulo_auditoria = None  # Debe definirse en el ViewSet

    def get_modulo_auditoria(self):
        if self.modulo_auditoria:
            return self.modulo_auditoria
        # Intento de inferir el módulo si no está definido
        return "SISTEMA"

    def perform_create(self, serializer):
        instance = serializer.save()
        AuditoriaService.registrar_accion(
            accion="CREAR",
            modulo=self.get_modulo_auditoria(),
            descripcion=f"Se creó un nuevo registro: {instance}",
            usuario=self.request.user,
            request=self.request,
            objeto=instance,
            datos_despues=snapshot_objeto(instance)
        )

    def perform_update(self, serializer):
        instance_antes = self.get_object()
        datos_antes = snapshot_objeto(instance_antes)
        
        instance = serializer.save()
        datos_despues = snapshot_objeto(instance)
        
        AuditoriaService.registrar_accion(
            accion="ACTUALIZAR",
            modulo=self.get_modulo_auditoria(),
            descripcion=f"Se actualizó el registro: {instance}",
            usuario=self.request.user,
            request=self.request,
            objeto=instance,
            datos_antes=datos_antes,
            datos_despues=datos_despues
        )

    def perform_destroy(self, instance):
        datos_antes = snapshot_objeto(instance)
        repr_instancia = str(instance)
        instance.delete()
        
        AuditoriaService.registrar_accion(
            accion="ELIMINAR",
            modulo=self.get_modulo_auditoria(),
            descripcion=f"Se eliminó el registro: {repr_instancia}",
            usuario=self.request.user,
            request=self.request,
            objeto=None,  # Ya no existe en DB
            objeto_repr=repr_instancia,
            datos_antes=datos_antes
        )
