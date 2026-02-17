# apps/compras/serializers/read.py
"""
🔹 SERIALIZERS DE LECTURA - Versión Mejorada
==============================================

Características:
- Incluye numero_compra en todas las respuestas
- Mejor estructura de datos relacionados
- Campos calculados optimizados
- Documentación inline

Autor: Sistema ERP
Versión: 2.0
Fecha: 2026-02-15
"""

from rest_framework import serializers
from django.db.models import Sum
from apps.compras.models import Compra, DetalleCompra
from apps.inventario.models import Producto
from apps.proveedores.serializers import ProveedorSimpleSerializer


# ============================================================================
# SERIALIZERS SIMPLES (para relaciones)
# ============================================================================


class ProductoCompraSerializer(serializers.ModelSerializer):
    """
    Serializer simple de producto para detalles de compra

    Campos:
    - Información básica del producto
    - Stock actual
    - Precios
    """

    stock_actual = serializers.SerializerMethodField()

    class Meta:
        model = Producto
        fields = [
            "id",
            "codigo",
            "nombre",
            "precio_compra",
            "precio_venta",
            "stock_actual",
        ]

    def get_stock_actual(self, obj):
        """Obtener stock actual del inventario"""
        try:
            return obj.inventario.stock_actual
        except:
            return 0


# ============================================================================
# SERIALIZERS DE DETALLE DE COMPRA (READ)
# ============================================================================


class DetalleCompraReadSerializer(serializers.ModelSerializer):
    """
    Serializer de lectura para Detalle de Compra

    Incluye:
    - Información del producto
    - Cálculos de margen
    - Subtotales
    """

    # Campos relacionados del producto
    producto_codigo = serializers.CharField(source="producto.codigo", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_info = ProductoCompraSerializer(source="producto", read_only=True)

    # Cálculos
    margen_potencial = serializers.SerializerMethodField()

    class Meta:
        model = DetalleCompra
        fields = [
            "id",
            "producto",
            "producto_codigo",
            "producto_nombre",
            "producto_info",
            "cantidad",
            "precio_compra",
            "subtotal",
            "margen_potencial",
        ]

    def get_margen_potencial(self, obj):
        """
        Calcular margen de ganancia potencial

        Compara precio de compra vs precio de venta actual
        """
        precio_venta = obj.producto.precio_venta
        precio_compra = obj.precio_compra

        ganancia_unitaria = precio_venta - precio_compra
        ganancia_total = ganancia_unitaria * obj.cantidad

        margen_porcentaje = 0
        if precio_compra > 0:
            margen_porcentaje = ((precio_venta - precio_compra) / precio_compra) * 100

        return {
            "precio_venta_actual": float(precio_venta),
            "ganancia_unitaria": float(ganancia_unitaria),
            "ganancia_total": float(ganancia_total),
            "margen_porcentaje": round(margen_porcentaje, 2),
        }


# ============================================================================
# SERIALIZERS DE COMPRA (READ)
# ============================================================================


class CompraListSerializer(serializers.ModelSerializer):
    """
    Serializer para listar compras (vista resumida)

    Usado en: GET /api/compras/

    Incluye:
    - Número de compra (COMP-00001)
    - Información del proveedor
    - Información del usuario
    - Totales y estadísticas
    """

    # Información del proveedor
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    proveedor_documento = serializers.CharField(
        source="proveedor.documento", read_only=True
    )
    proveedor_info = ProveedorSimpleSerializer(source="proveedor", read_only=True)

    # Información del usuario
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    # Estadísticas
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()

    # Badge de estado (para UI)
    estado_badge = serializers.SerializerMethodField()

    # Resumen de productos (para tooltip o detalles rápidos)
    productos_resumen = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = [
            "id",
            "numero_compra",  # 🔹 NUEVO CAMPO
            "proveedor",
            "proveedor_nombre",
            "proveedor_documento",
            "proveedor_info",
            "usuario",
            "usuario_nombre",
            "usuario_email",
            "total",
            "total_productos",
            "total_unidades",
            "fecha",
            "estado",
            "estado_badge",  # 🔹 Para el frontend
            "created_at",
            "productos_resumen",
        ]

    def get_total_productos(self, obj):
        """Total de productos diferentes"""
        return obj.detalles.count()

    def get_total_unidades(self, obj):
        """Total de unidades compradas"""
        total = obj.detalles.aggregate(total=Sum("cantidad"))["total"]
        return total or 0

    def get_estado_badge(self, obj):
        """
        Información para renderizar badge en el frontend

        Returns:
            dict: color, texto, icono
        """
        badges = {
            "PENDIENTE": {"color": "warning", "texto": "Pendiente", "icono": "⏳"},
            "REALIZADA": {"color": "success", "texto": "Realizada", "icono": "✓"},
            "ANULADA": {"color": "danger", "texto": "Anulada", "icono": "✗"},
        }
        return badges.get(obj.estado, badges["PENDIENTE"])

    def get_productos_resumen(self, obj):
        detalles = obj.detalles.select_related("producto").all()
        return ", ".join([d.producto.nombre for d in detalles])

class CompraDetailSerializer(serializers.ModelSerializer):
    """
    Serializer para detalle completo de compra

    Usado en: GET /api/compras/{id}/

    Incluye:
    - Toda la información de la compra
    - Detalles de productos
    - Estadísticas y márgenes
    - Historial de cambios (si existe)
    """

    # Información del proveedor
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    proveedor_info = ProveedorSimpleSerializer(source="proveedor", read_only=True)

    # Información del usuario
    usuario_nombre = serializers.CharField(source="usuario.username", read_only=True)
    usuario_email = serializers.EmailField(source="usuario.email", read_only=True)

    # Detalles de productos
    detalles = DetalleCompraReadSerializer(many=True, read_only=True)

    # Estadísticas calculadas
    total_productos = serializers.SerializerMethodField()
    total_unidades = serializers.SerializerMethodField()
    margen_potencial = serializers.SerializerMethodField()

    # Badge de estado
    estado_badge = serializers.SerializerMethodField()

    # Información de auditoría
    puede_editar = serializers.SerializerMethodField()
    puede_confirmar = serializers.SerializerMethodField()
    puede_anular = serializers.SerializerMethodField()

    class Meta:
        model = Compra
        fields = [
            "id",
            "numero_compra",  # 🔹 NUEVO
            "proveedor",
            "proveedor_nombre",
            "proveedor_info",
            "usuario",
            "usuario_nombre",
            "usuario_email",
            "total",
            "detalles",
            "total_productos",
            "total_unidades",
            "margen_potencial",
            "fecha",
            "estado",
            "estado_badge",
            "motivo_anulacion",
            "created_at",
            # Permisos (para UI)
            "puede_editar",
            "puede_confirmar",
            "puede_anular",
        ]

    def get_total_productos(self, obj):
        """Total de productos diferentes"""
        return obj.detalles.count()

    def get_total_unidades(self, obj):
        """Total de unidades compradas"""
        total = obj.detalles.aggregate(total=Sum("cantidad"))["total"]
        return total or 0

    def get_margen_potencial(self, obj):
        """
        Calcular margen de ganancia potencial total

        Compara precio de compra vs precio de venta actual de todos los productos
        """
        valor_compra = float(obj.total)
        valor_venta_potencial = 0

        for detalle in obj.detalles.all():
            valor_venta_potencial += float(
                detalle.producto.precio_venta * detalle.cantidad
            )

        ganancia_total = valor_venta_potencial - valor_compra

        margen_porcentaje = 0
        if valor_compra > 0:
            margen_porcentaje = (ganancia_total / valor_compra) * 100

        return {
            "valor_compra": valor_compra,
            "valor_venta_potencial": valor_venta_potencial,
            "ganancia_potencial": ganancia_total,
            "margen_porcentaje": round(margen_porcentaje, 2),
        }

    def get_estado_badge(self, obj):
        """Badge para el frontend"""
        badges = {
            "PENDIENTE": {"color": "warning", "texto": "Pendiente", "icono": "⏳"},
            "REALIZADA": {"color": "success", "texto": "Realizada", "icono": "✓"},
            "ANULADA": {"color": "danger", "texto": "Anulada", "icono": "✗"},
        }
        return badges.get(obj.estado, badges["PENDIENTE"])

    def get_puede_editar(self, obj):
        """Solo se puede editar si está PENDIENTE"""
        return obj.estado == "PENDIENTE"

    def get_puede_confirmar(self, obj):
        """Solo se puede confirmar si está PENDIENTE"""
        return obj.estado == "PENDIENTE"

    def get_puede_anular(self, obj):
        """Solo se puede anular si NO está ANULADA"""
        return obj.estado != "ANULADA"


class CompraSimpleSerializer(serializers.ModelSerializer):
    """
    Serializer simple para uso en relaciones

    Usado en:
    - Reportes
    - Referencias en otras entidades
    """

    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)

    class Meta:
        model = Compra
        fields = [
            "id",
            "numero_compra",
            "proveedor",
            "proveedor_nombre",
            "total",
            "fecha",
            "estado",
        ]
