import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.productos.models import Producto
from apps.proveedores.models import Proveedor
from apps.usuarios.models import Usuario
from apps.compras.services import CompraService
from decimal import Decimal
from datetime import date

def test():
    # Obtener un proveedor
    proveedor = Proveedor.objects.first()
    if not proveedor:
        print("No hay proveedores")
        return
    # Obtener un producto
    producto = Producto.objects.first()
    if not producto:
        print("No hay productos")
        return
    # Obtener un usuario
    usuario = Usuario.objects.first()
    if not usuario:
        print("No hay usuarios")
        return

    print(f"Proveedor: {proveedor.nombre} (ID: {proveedor.id})")
    print(f"Producto: {producto.nombre} (ID: {producto.id})")
    print(f"Usuario: {usuario.username} (ID: {usuario.id})")

    detalles = [
        {
            "producto_id": producto.id,
            "cantidad": 2,
            "precio_compra": Decimal("2500000.00"),
            "guardar_en_lista_precio": True
        }
    ]

    try:
        compra = CompraService.crear_compra(
            proveedor=proveedor,
            detalles=detalles,
            usuario=usuario,
            fecha=date.today(),
            observaciones="Test de compra asíncrona"
        )
        print(f"Compra creada con éxito! ID: {compra.id}")
        
        # Verificar si el precio se guardó en la lista de precios
        from apps.precios.models import ListaPrecioCompra
        precios = ListaPrecioCompra.objects.filter(producto=producto, proveedor=proveedor, vigente=True)
        print(f"Precios vigentes encontrados: {precios.count()}")
        for p in precios:
            print(f" - ID: {p.id}, Precio: {p.precio}, Vigente: {p.vigente}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
