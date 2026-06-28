import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch

from apps.facturacion.models import Factura, FacturaDetalle, PagoFactura
from apps.documentos.models import Documento
from apps.facturacion.services.factura_venta_service import FacturaVentaService
from apps.facturacion.services.pago_factura_service import PagoFacturaService
from apps.clientes.models import Cliente
from apps.productos.models import Producto

User = get_user_model()

class FlujoFacturacionTestCase(TestCase):
    """
    Test de Integración del Flujo de Facturación:
    BORRADOR -> EMITIDA -> PAGADA -> ANULADA
    """

    def setUp(self):
        # Configurar dependencias
        self.user = User.objects.create_user(username='test_admin', password='123')
        self.cliente = Cliente.objects.create(nombre="Cliente Test", numero_documento="123456")
        self.producto = Producto.objects.create(nombre="Producto Test", codigo="PT1", precio=Decimal("100.00"))
        
        self.detalles_data = [
            {
                'producto_id': self.producto.id,
                'cantidad': Decimal("2.00"),
                'precio_unitario': Decimal("100.00"),
                'descuento': Decimal("0.00"),
                'impuestos_linea': Decimal("0.00")
            }
        ]

    def test_flujo_completo_facturacion(self):
        # 1. CREACIÓN BORRADOR
        factura = FacturaVentaService.crear_borrador(
            cliente_id=self.cliente.id,
            vendedor_id=None,
            detalles_data=self.detalles_data,
            usuario=self.user
        )
        
        self.assertEqual(factura.estado, "BORRADOR")
        self.assertEqual(factura.total, Decimal("200.00"))
        self.assertIsNone(factura.documento)
        
        # Mocks para servicios externos
        with patch('apps.facturacion.services.inventario_factura_service.InventarioFacturaService.descontar_stock') as mock_desc_stock, \
             patch('apps.facturacion.services.inventario_factura_service.InventarioFacturaService.revertir_stock') as mock_rev_stock, \
             patch('apps.caja.services.caja_control.CajaControlService.verificar_caja_abierta') as mock_caja_abierta, \
             patch('apps.caja.services.caja_service.CajaService.registrar_movimiento') as mock_reg_movimiento:
            
            class MockSesion:
                id = 1
            mock_caja_abierta.return_value = MockSesion()

            # 2. EMISIÓN
            factura = FacturaVentaService.emitir_factura(factura, self.user)
            
            self.assertEqual(factura.estado, "EMITIDA")
            self.assertIsNotNone(factura.numero)
            self.assertIsNotNone(factura.documento)
            self.assertEqual(factura.documento.estado, Documento.Estado.EMITIDO)
            mock_desc_stock.assert_called_once_with(factura, self.user)

            # 3. REGISTRO DE PAGO (PAGADA)
            # Para registrar el pago necesitamos un método de pago ficticio
            pago = PagoFacturaService.registrar_pago(
                factura=factura,
                metodo_pago_id=1,  # Ficticio, asumimos que existe o lo ignoramos por el mock si no valida BD (falla si valida BD)
                monto=Decimal("200.00"),
                usuario=self.user
            )
            
            self.assertEqual(factura.estado, "PAGADA")
            self.assertEqual(factura.saldo_pendiente, Decimal("0.00"))
            mock_reg_movimiento.assert_called()

            # 4. ANULACIÓN
            factura = FacturaVentaService.anular_factura(factura, self.user, motivo="Prueba de anulación")
            
            self.assertEqual(factura.estado, "ANULADA")
            self.assertEqual(factura.documento.estado, Documento.Estado.ANULADO)
            mock_rev_stock.assert_called_once_with(factura, self.user)
