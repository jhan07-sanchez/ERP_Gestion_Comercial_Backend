# apps/dashboard/serializers/read.py
"""
Serializers del Dashboard

En este caso los serializers NO validan modelos (no hay modelos propios).
Su función es DOCUMENTAR y ESTRUCTURAR las respuestas de la API.

¿Por qué usar serializers sin modelo?
- Consistencia con el patrón de otras apps
- Facilita documentación automática (Swagger/OpenAPI)
- Permite validar parámetros de entrada fácilmente

Autor: Sistema ERP
"""

from rest_framework import serializers


# ============================================================================
# SERIALIZERS DE PARÁMETROS (Input)
# ============================================================================


class FiltroFechasSerializer(serializers.Serializer):
    """
    Serializer para validar parámetros de filtro por fechas.
    Usado como query params en varios endpoints del dashboard.

    Ejemplo de uso en la view:
        serializer = FiltroFechasSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        fecha_inicio = serializer.validated_data.get('fecha_inicio')
    """

    fecha_inicio = serializers.DateField(required=False, format="%Y-%m-%d")
    fecha_fin = serializers.DateField(required=False, format="%Y-%m-%d")

    def validate(self, data):
        """Validar que fecha_inicio <= fecha_fin"""
        inicio = data.get("fecha_inicio")
        fin = data.get("fecha_fin")
        if inicio and fin and inicio > fin:
            raise serializers.ValidationError(
                "La fecha de inicio no puede ser mayor que la fecha de fin."
            )
        return data


class FiltroGraficoSerializer(serializers.Serializer):
    """
    Parámetros para los endpoints de gráficos.
    """

    PERIODO_CHOICES = [("semana", "Semana"), ("mes", "Mes"), ("año", "Año")]
    AGRUPACION_CHOICES = [("dia", "Día"), ("semana", "Semana"), ("mes", "Mes")]

    periodo = serializers.ChoiceField(
        choices=PERIODO_CHOICES,
        default="mes",
        required=False,
        help_text="Rango de tiempo: semana, mes, año",
    )
    agrupacion = serializers.ChoiceField(
        choices=AGRUPACION_CHOICES,
        default="dia",
        required=False,
        help_text="Cómo agrupar los datos: dia, semana, mes",
    )


class FiltroTopSerializer(serializers.Serializer):
    """
    Parámetros para endpoints de top (productos, clientes).
    """

    limite = serializers.IntegerField(
        min_value=1,
        max_value=50,
        default=10,
        required=False,
        help_text="Número máximo de resultados (1-50)",
    )
    fecha_inicio = serializers.DateField(required=False, format="%Y-%m-%d")
    fecha_fin = serializers.DateField(required=False, format="%Y-%m-%d")
