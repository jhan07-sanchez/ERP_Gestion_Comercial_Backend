from django.db import transaction
from apps.configuracion.services.configuracion_service import ConfiguracionService

class NumeracionFacturaService:
    """
    Servicio encargado de generar los números de factura (consecutivos)
    centralizado desde ConfiguracionGeneral.
    """

    @staticmethod
    def generar_siguiente_numero(codigo_secuencia: str = "factura_venta") -> str:
        """
        Obtiene de forma atómica el siguiente número disponible para una secuencia.
        Usa la configuración global maestra.
        """
        # La lógica de transacción atómica y avance de consecutivo 
        # está encapsulada en ConfiguracionService.generar_numero_factura()
        return ConfiguracionService.generar_numero_factura()
