from django.db import transaction
from apps.documentos.models import SecuenciaNumeracionDocumento

class NumeracionFacturaService:
    """
    Servicio encargado de generar los números de factura (consecutivos)
    de forma segura y atómica.
    """

    @staticmethod
    def generar_siguiente_numero(codigo_secuencia: str = "factura_venta") -> str:
        """
        Obtiene de forma atómica el siguiente número disponible para una secuencia.
        Por defecto usa 'factura_venta'.
        """
        with transaction.atomic():
            # select_for_update bloquea la fila hasta que termine la transacción,
            # previniendo condiciones de carrera (números duplicados).
            secuencia, creada = SecuenciaNumeracionDocumento.objects.select_for_update().get_or_create(
                codigo=codigo_secuencia,
                defaults={
                    "prefijo": "FV",
                    "ultimo_numero": 0
                }
            )
            
            secuencia.ultimo_numero += 1
            secuencia.save(update_fields=["ultimo_numero"])
            
            # Ejemplo: FV-000001
            numero_formateado = f"{secuencia.prefijo}-{str(secuencia.ultimo_numero).zfill(6)}"
            
            return numero_formateado
