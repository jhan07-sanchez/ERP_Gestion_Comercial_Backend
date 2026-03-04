# apps/auditorias/services/auditoria_service.py
import logging
from typing import Optional, Any, Dict, List
from django.db import transaction
from apps.auditorias.utils import registrar_log, snapshot_objeto

logger = logging.getLogger("auditorias")

class AuditoriaService:
    @staticmethod
    def calcular_diff(antes: Dict, despues: Dict) -> Dict:
        """
        Compara dos dicts y devuelve solo las diferencias.
        """
        diff = {}
        # Union de todas las llaves
        keys = set(antes.keys()) | set(despues.keys())
        
        for key in keys:
            val_antes = antes.get(key)
            val_despues = despues.get(key)
            
            if val_antes != val_despues:
                diff[key] = {
                    "antes": val_antes,
                    "despues": val_despues
                }
        return diff

    @classmethod
    def registrar_accion(
        cls,
        accion: str,
        modulo: str,
        descripcion: str,
        usuario=None,
        request=None,
        objeto=None,
        datos_antes: Optional[Dict] = None,
        datos_despues: Optional[Dict] = None,
        extra: Optional[Dict] = None,
        nivel: str = "INFO",
        exitoso: bool = True
    ):
        """
        Punto de entrada unificado para registrar acciones, calculando diff si es necesario.
        """
        final_extra = extra or {}
        
        # Si tenemos antes y después, calculamos el diff para guardarlo en extra
        if datos_antes is not None and datos_despues is not None:
            diff = cls.calcular_diff(datos_antes, datos_despues)
            final_extra["diff"] = diff

        return registrar_log(
            accion=accion,
            modulo=modulo,
            descripcion=descripcion,
            usuario=usuario,
            request=request,
            objeto=objeto,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            extra=final_extra,
            nivel=nivel,
            exitoso=exitoso
        )
