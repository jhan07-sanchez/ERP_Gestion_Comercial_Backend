# apps/categorias/services/categoria_service.py
"""
Servicio de Lógica de Negocio para Categorías

Los servicios encapsulan la lógica compleja y mantienen
los ViewSets limpios y enfocados en la capa HTTP.
"""

from django.db.models import Sum, Count, F
from apps.categorias.models import Categoria


# ============================================================================
# SERVICIO DE CATEGORÍAS
# ============================================================================

class CategoriaService:
    """Servicio para manejar la lógica de negocio de Categorías"""

    @staticmethod
    def crear_categoria(nombre, descripcion=None, estado=True):
        """
        Crear una nueva categoría

        Args:
            nombre: Nombre de la categoría
            descripcion: Descripción opcional

        Returns:
            Categoria: Instancia de la categoría creada
        """
        categoria = Categoria.objects.create(
            nombre=nombre.strip().title(),
            descripcion=descripcion.strip() if descripcion else None,
            estado=estado
        )
        return categoria

    @staticmethod
    def actualizar_categoria(categoria_id, nombre=None, descripcion=None, estado=None):
        """
        Actualizar una categoría existente

        Args:
            categoria_id: ID de la categoría
            nombre: Nuevo nombre (opcional)
            descripcion: Nueva descripción (opcional)
            estado: Nuevo estado (opcional)

        Returns:
            Categoria: Instancia de la categoría actualizada
        """
        categoria = Categoria.objects.get(id=categoria_id)

        if nombre:
            categoria.nombre = nombre.strip().title()

        if descripcion is not None:
            categoria.descripcion = descripcion.strip() if descripcion else None

        if estado is not None:
            categoria.estado = estado

        categoria.save()
        return categoria

    @staticmethod
    def eliminar_categoria(categoria_id):
        """
        Eliminar una categoría (solo si no tiene productos)

        Args:
            categoria_id: ID de la categoría

        Raises:
            ValueError: Si la categoría tiene productos asignados
        """
        categoria = Categoria.objects.get(id=categoria_id)

        # Verificar que no tenga productos
        total_productos = categoria.productos.count()
        if total_productos > 0:
            raise ValueError(
                f'No se puede eliminar la categoría "{categoria.nombre}" '
                f'porque tiene {total_productos} producto(s) asignado(s).'
            )

        categoria.delete()

    @staticmethod
    def obtener_estadisticas_categoria(categoria_id):
        """
        Obtener estadísticas de una categoría

        Returns:
            dict: Estadísticas de la categoría
        """
        categoria = Categoria.objects.get(id=categoria_id)
        productos = categoria.productos.all()

        estadisticas = {
            'id': categoria.id,
            'nombre': categoria.nombre,
            'total_productos': productos.count(),
            'productos_activos': productos.filter(estado=True).count(),
            'productos_inactivos': productos.filter(estado=False).count(),
            'stock_total': sum([
                p.inventario.stock_actual
                for p in productos
                if hasattr(p, 'inventario')
            ]),
            'valor_inventario': sum([
                p.inventario.stock_actual * p.precio_compra
                for p in productos
                if hasattr(p, 'inventario')
            ]),
            'productos_stock_bajo': productos.filter(
                inventario__stock_actual__lte=F('stock_minimo')
            ).count() if productos.exists() else 0
        }

        return estadisticas
