# apps/auditorias/serializers.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SERIALIZERS DE AUDITORÍA - ERP                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿QUÉ HACE UN SERIALIZER EN DRF?
════════════════════════════════
Convierte objetos Python (instancias de modelos Django) ↔ JSON para la API.

En auditorías solo necesitamos READ serializers porque:
  - Los logs son de SOLO LECTURA desde la API
  - Solo el sistema puede crear logs (no el usuario)

Autor: Sistema ERP
"""

from rest_framework import serializers
from apps.auditorias.models import LogAuditoria


class UsuarioAuditoriaSerializer(serializers.Serializer):
    """Información básica del usuario para el log."""

    id = serializers.IntegerField()
    username = serializers.CharField()
    nombre_completo = serializers.SerializerMethodField()

    def get_nombre_completo(self, obj):
        return obj.get_full_name() or obj.username


class LogAuditoriaListSerializer(serializers.ModelSerializer):
    """
    Serializer para LISTAR logs (versión resumida).

    Usado en: GET /api/auditorias/logs/
    """

    accion_display = serializers.CharField(source="get_accion_display", read_only=True)
    modulo_display = serializers.CharField(source="get_modulo_display", read_only=True)
    nivel_display = serializers.CharField(source="get_nivel_display", read_only=True)
    usuario_info = serializers.SerializerMethodField()
    icono = serializers.CharField(source="icono_accion", read_only=True)

    class Meta:
        model = LogAuditoria
        fields = [
            "id",
            "fecha_hora",
            "usuario_nombre",
            "usuario_info",
            "accion",
            "accion_display",
            "modulo",
            "modulo_display",
            "nivel",
            "nivel_display",
            "descripcion",
            "ip_address",
            "exitoso",
            "icono",
            "objeto_repr",
            "duracion_ms",
        ]

    def get_usuario_info(self, obj):
        if obj.usuario:
            return {
                "id": obj.usuario.id,
                "username": obj.usuario.username,
                "nombre": obj.usuario.get_full_name() or obj.usuario.username,
            }
        return None


class LogAuditoriaDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para VER UN LOG en detalle.

    Incluye todos los campos, incluyendo datos_antes/despues.

    Usado en: GET /api/auditorias/logs/{id}/
    """

    accion_display = serializers.CharField(source="get_accion_display", read_only=True)
    modulo_display = serializers.CharField(source="get_modulo_display", read_only=True)
    nivel_display = serializers.CharField(source="get_nivel_display", read_only=True)
    usuario_info = serializers.SerializerMethodField()
    icono = serializers.CharField(source="icono_accion", read_only=True)
    tiene_cambios = serializers.BooleanField(read_only=True)
    tipo_objeto = serializers.SerializerMethodField()
    diff = serializers.SerializerMethodField()

    class Meta:
        model = LogAuditoria
        fields = "__all__"
        extra_fields = [
            "accion_display",
            "modulo_display",
            "nivel_display",
            "usuario_info",
            "icono",
            "tiene_cambios",
            "tipo_objeto",
            "diff",
        ]

    def get_usuario_info(self, obj):
        if obj.usuario:
            return {
                "id": obj.usuario.id,
                "username": obj.usuario.username,
                "nombre": obj.usuario.get_full_name() or obj.usuario.username,
                "email": obj.usuario.email,
            }
        return {"nombre": obj.usuario_nombre or "Sistema"}

    def get_tipo_objeto(self, obj):
        if obj.content_type:
            return {
                "app": obj.content_type.app_label,
                "modelo": obj.content_type.model,
                "nombre": obj.content_type.name,
            }
        return None

    def get_diff(self, obj):
        """Extrae el diff del campo extra si existe."""
        if obj.extra and isinstance(obj.extra, dict):
            return obj.extra.get("diff")
        return None


class EstadisticasAuditoriaSerializer(serializers.Serializer):
    """
    Serializer para las estadísticas del dashboard de auditorías.

    Usado en: GET /api/auditorias/estadisticas/
    """

    total_logs = serializers.IntegerField()
    logs_hoy = serializers.IntegerField()
    logs_semana = serializers.IntegerField()
    errores_hoy = serializers.IntegerField()
    accesos_denegados = serializers.IntegerField()
    logins_fallidos = serializers.IntegerField()
    usuarios_activos = serializers.IntegerField()
    por_modulo = serializers.DictField()
    por_accion = serializers.DictField()
    por_nivel = serializers.DictField()
    actividad_reciente = serializers.ListField()
