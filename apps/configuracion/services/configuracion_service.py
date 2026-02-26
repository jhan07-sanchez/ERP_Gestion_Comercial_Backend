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
from apps.configuracion.models import ConfiguracionGeneral


class ConfiguracionService:
    """
    Servicio para manejar la lógica de negocio de la Configuración General.

    Todos los métodos son @staticmethod porque no necesitan estado propio:
    solo reciben datos, hacen su trabajo y retornan resultados.
    """

    @staticmethod
    def obtener_configuracion():
        """
        Obtiene la configuración general del sistema.

        Usa el método .obtener() del modelo que implementa el patrón Singleton.
        Si no existe configuración, la crea con valores por defecto.

        Retorna:
            ConfiguracionGeneral: La instancia única de configuración.

        Uso:
            config = ConfiguracionService.obtener_configuracion()
        """
        return ConfiguracionGeneral.obtener()

    @staticmethod
    @transaction.atomic
    def actualizar_configuracion(datos_validados: dict) -> ConfiguracionGeneral:
        """
        Actualiza la configuración general con los datos proporcionados.

        @transaction.atomic significa que si algo falla en el proceso,
        todos los cambios se revierten (rollback). Esto protege la integridad
        de los datos.

        Args:
            datos_validados (dict): Datos ya validados por el serializer.
                                    No pasar datos sin validar aquí.

        Retorna:
            ConfiguracionGeneral: La instancia actualizada.

        Proceso:
            1. Obtiene la configuración actual (la crea si no existe)
            2. Actualiza cada campo con los datos nuevos
            3. Guarda y retorna
        """
        config = ConfiguracionGeneral.obtener()

        # Actualizar cada campo que venga en los datos
        # setattr(objeto, 'campo', valor) es equivalente a objeto.campo = valor
        # pero funciona de forma dinámica con cualquier nombre de campo
        for campo, valor in datos_validados.items():
            setattr(config, campo, valor)

        config.save()
        return config

    @staticmethod
    @transaction.atomic
    def reset_consecutivo(tipo: str, nuevo_consecutivo: int) -> ConfiguracionGeneral:
        """
        Resetea o ajusta el consecutivo de un tipo de documento.

        ⚠️ ACCIÓN CRÍTICA: Cambiar un consecutivo puede causar documentos
        con números duplicados. Solo debe hacerlo el Administrador.

        ¿Por qué select_for_update()?
        - En sistemas concurrentes (múltiples usuarios), dos personas
          podrían intentar cambiar el consecutivo al mismo tiempo.
        - select_for_update() bloquea el registro hasta que la transacción
          termine, evitando condiciones de carrera.

        Args:
            tipo (str): Tipo de documento. Valores: "factura", "compra", "recibo"
            nuevo_consecutivo (int): El nuevo valor del consecutivo (≥ 1)

        Retorna:
            ConfiguracionGeneral: La instancia actualizada.

        Raises:
            ValueError: Si el tipo no es válido.
        """
        # Bloquear el registro para escritura exclusiva
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)

        # Mapa de tipos a campos del modelo
        # Esto es más limpio que un if/elif por cada tipo
        campo_mapa = {
            "factura": "consecutivo_factura",
            "compra": "consecutivo_compra",
            "recibo": "consecutivo_recibo",
        }

        if tipo not in campo_mapa:
            raise ValueError(
                f"Tipo de documento no válido: '{tipo}'. "
                f"Valores permitidos: {list(campo_mapa.keys())}"
            )

        campo = campo_mapa[tipo]
        setattr(config, campo, nuevo_consecutivo)
        config.save(update_fields=[campo])

        return config

    @staticmethod
    def obtener_info_empresa() -> dict:
        """
        Retorna un diccionario con la información de la empresa.

        Útil para:
        - Generación de PDFs (facturas, recibos, reportes)
        - Mostrar datos en el encabezado de la aplicación
        - Cualquier contexto que necesite los datos de la empresa

        Retorna:
            dict: Diccionario con los datos de la empresa
        """
        config = ConfiguracionGeneral.obtener()
        return config.get_info_empresa()

    @staticmethod
    def generar_numero_factura() -> str:
        """
        Genera el próximo número de factura.

        ¿Por qué está en el servicio y no directamente en el modelo?
        - Porque en el futuro podríamos querer registrar cada generación
          en un log, o notificar a alguien, sin cambiar el modelo.
        - El servicio es el lugar correcto para orquestar estas acciones.

        Retorna:
            str: El número de factura generado (ej: "FAC-0005")
        """
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        return config.generar_numero_factura()

    @staticmethod
    def generar_numero_compra() -> str:
        """
        Genera el próximo número de compra.
        Retorna str como "COM-0003"
        """
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        return config.generar_numero_compra()

    @staticmethod
    def generar_numero_recibo() -> str:
        """
        Genera el próximo número de recibo POS.
        Retorna str como "REC-0012"
        """
        config = ConfiguracionGeneral.objects.select_for_update().get(pk=1)
        return config.generar_numero_recibo()
