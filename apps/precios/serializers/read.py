# apps/precio/serializers/read.py
"""
SERIALIZERS DE LECTURA para la app Precio

¿Qué es un serializer de LECTURA?
───────────────────────────────────
Cuando alguien hace GET /api/precios/, Django necesita convertir
los objetos Python (instancias del modelo) a JSON para enviar al frontend.

Ese proceso de conversión es la LECTURA (leer de la DB → JSON).

¿Por qué separar READ de WRITE?
────────────────────────────────
- En READ quieres mostrar: nombre del producto, nombre del proveedor,
  campos calculados como "¿está en oferta?", etc.
- En WRITE solo recibes: producto_id, proveedor_id, precio.
- Son responsabilidades diferentes.

SerializerMethodField:
──────────────────────
Es un campo "especial" que ejecuta un método Python para calcular su valor.
Ejemplo:
    estado_badge = SerializerMethodField()
    def get_estado_badge(self, obj): ...
Django automáticamente llama al método que empieza con 'get_' + nombre del campo.
"""

from rest_framework import serializers
from apps.precios.models import ListaPrecioCompra


# ============================================================================
# SERIALIZER DE LISTA (Vista resumida — para GET /api/precios/)
# ============================================================================


class ListaPrecioCompraListSerializer(serializers.ModelSerializer):
    """
    Serializer resumido para la lista de precios.

    Usado en: GET /api/precios/
    Incluye nombres legibles de producto y proveedor (no solo IDs).
    """

    # Campos de relaciones: en lugar de mostrar solo el ID,
    # mostramos el nombre completo del objeto relacionado.
    # 'source' le dice al serializer de dónde tomar el valor.
    producto_nombre = serializers.CharField(
        source="producto.nombre",
        read_only=True,
    )
    producto_codigo = serializers.CharField(
        source="producto.codigo",
        read_only=True,
    )
    proveedor_nombre = serializers.CharField(
        source="proveedor.nombre",
        read_only=True,
    )
    proveedor_documento = serializers.CharField(
        source="proveedor.documento",
        read_only=True,
    )

    # SerializerMethodField: campo calculado en Python, no en la DB
    estado_badge = serializers.SerializerMethodField()
    vigencia_info = serializers.SerializerMethodField()

    class Meta:
        model = ListaPrecioCompra
        fields = [
            "id",
            # Producto
            "producto",
            "producto_codigo",
            "producto_nombre",
            # Proveedor
            "proveedor",
            "proveedor_nombre",
            "proveedor_documento",
            # Precio
            "precio",
            # Estado
            "vigente",
            "estado_badge",
            # Fechas
            "fecha_inicio",
            "fecha_fin",
            "vigencia_info",
            "fecha_creacion",
        ]

    def get_estado_badge(self, obj):
        """
        Retorna información visual para el badge de estado.

        ¿Por qué retornar un dict en lugar del boolean directamente?
        Porque el frontend puede usar directamente el color, texto e ícono
        sin tener que calcular nada. Esto es un principio de diseño de API
        llamado "client-friendly responses".
        """
        if obj.vigente:
            return {
                "texto": "VIGENTE",
                "color": "green",
                "icono": "✓",
                "clase": "badge-success",
            }
        return {
            "texto": "HISTÓRICO",
            "color": "gray",
            "icono": "⏱",
            "clase": "badge-secondary",
        }

    def get_vigencia_info(self, obj):
        """
        Información sobre el período de vigencia del precio.
        Ayuda al frontend a mostrar "Válido desde X hasta Y".
        """
        from django.utils import timezone

        ahora = timezone.now()

        if not obj.vigente:
            return {
                "estado": "expirado",
                "mensaje": "Precio histórico (ya no está vigente)",
                "dias_vigente": None,
            }

        dias = (ahora - obj.fecha_inicio).days
        return {
            "estado": "vigente",
            "mensaje": f"Vigente hace {dias} día(s)",
            "dias_vigente": dias,
        }


# ============================================================================
# SERIALIZER DE DETALLE (Vista completa — para GET /api/precios/{id}/)
# ============================================================================


class ListaPrecioCompraDetailSerializer(serializers.ModelSerializer):
    """
    Serializer completo para el detalle de un precio.

    Usado en: GET /api/precios/{id}/
    Incluye TODA la información, incluyendo datos completos del producto
    y proveedor, y el historial de precios.
    """

    # Campos de relaciones con todos los datos
    producto_info = serializers.SerializerMethodField()
    proveedor_info = serializers.SerializerMethodField()

    estado_badge = serializers.SerializerMethodField()
    vigencia_info = serializers.SerializerMethodField()

    # Variación respecto al precio anterior
    variacion_precio = serializers.SerializerMethodField()

    class Meta:
        model = ListaPrecioCompra
        fields = [
            "id",
            # Producto completo
            "producto",
            "producto_info",
            # Proveedor completo
            "proveedor",
            "proveedor_info",
            # Precio con contexto
            "precio",
            "variacion_precio",
            # Estado
            "vigente",
            "estado_badge",
            # Fechas
            "fecha_inicio",
            "fecha_fin",
            "vigencia_info",
            "fecha_creacion",
        ]

    def get_producto_info(self, obj):
        """Retorna datos básicos del producto."""
        p = obj.producto
        return {
            "id": p.id,
            "codigo": p.codigo,
            "nombre": p.nombre,
            "precio_venta": float(p.precio_venta),
            "precio_compra_actual": float(p.precio_compra),
        }

    def get_proveedor_info(self, obj):
        """Retorna datos básicos del proveedor."""
        pr = obj.proveedor
        return {
            "id": pr.id,
            "nombre": pr.nombre,
            "documento": pr.documento,
            "telefono": pr.telefono or "-",
            "email": pr.email or "-",
        }

    def get_estado_badge(self, obj):
        if obj.vigente:
            return {"texto": "VIGENTE", "color": "green", "icono": "✓"}
        return {"texto": "HISTÓRICO", "color": "gray", "icono": "⏱"}

    def get_vigencia_info(self, obj):
        from django.utils import timezone

        ahora = timezone.now()
        dias = (ahora - obj.fecha_inicio).days

        if not obj.vigente and obj.fecha_fin:
            duracion = (obj.fecha_fin - obj.fecha_inicio).days
            return {
                "estado": "expirado",
                "fecha_inicio": obj.fecha_inicio,
                "fecha_fin": obj.fecha_fin,
                "duracion_dias": duracion,
            }

        return {
            "estado": "vigente",
            "fecha_inicio": obj.fecha_inicio,
            "fecha_fin": None,
            "dias_transcurridos": dias,
        }

    def get_variacion_precio(self, obj):
        """
        Calcula la variación respecto al precio anterior de este
        mismo producto con este mismo proveedor.

        Útil para saber si subió o bajó el precio.
        """
        precio_anterior = (
            ListaPrecioCompra.objects.filter(
                producto=obj.producto,
                proveedor=obj.proveedor,
                vigente=False,
            )
            .order_by("-fecha_fin")
            .first()
        )

        if not precio_anterior:
            return {
                "tiene_historial": False,
                "variacion_absoluta": 0,
                "variacion_porcentual": 0,
                "tendencia": "nuevo",
            }

        diferencia = float(obj.precio) - float(precio_anterior.precio)
        porcentaje = 0
        if float(precio_anterior.precio) > 0:
            porcentaje = (diferencia / float(precio_anterior.precio)) * 100

        return {
            "tiene_historial": True,
            "precio_anterior": float(precio_anterior.precio),
            "variacion_absoluta": round(diferencia, 2),
            "variacion_porcentual": round(porcentaje, 2),
            "tendencia": "subio"
            if diferencia > 0
            else "bajo"
            if diferencia < 0
            else "igual",
            "fecha_precio_anterior": precio_anterior.fecha_fin,
        }


# ============================================================================
# SERIALIZER SIMPLE (Para usar en relaciones con otros módulos)
# ============================================================================


class ListaPrecioCompraSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer mínimo. Usado cuando otro módulo (ej: compras)
    necesita mostrar el precio de un producto sin toda la info detallada.
    """

    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = ListaPrecioCompra
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "proveedor",
            "proveedor_nombre",
            "precio",
        ]
