import abc
import uuid
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class DianResponse:
    """
    Estructura de respuesta estandarizada para cualquier adaptador DIAN.
    """
    exitoso: bool
    cufe: Optional[str] = None
    qr_code: Optional[str] = None
    xml_firmado: Optional[str] = None
    mensaje: str = ""
    codigo_respuesta: str = ""
    fecha_validacion: Optional[datetime] = None
    errores: list = field(default_factory=list)


class DianAdapterBase(abc.ABC):
    """
    Puerto (interfaz) para el adaptador de Facturación Electrónica DIAN.

    Cualquier proveedor de facturación electrónica (Carvajal, The Factory HKA,
    Saphety, etc.) debe implementar esta interfaz para integrarse al sistema.

    Patrón: Port/Adapter (Hexagonal Architecture).
    """

    @abc.abstractmethod
    def firmar_y_enviar_factura(self, factura_data: dict) -> DianResponse:
        """Firma digitalmente una factura y la envía a la DIAN."""
        ...

    @abc.abstractmethod
    def firmar_y_enviar_nota_credito(self, nota_data: dict) -> DianResponse:
        """Firma y envía una Nota de Crédito electrónica."""
        ...

    @abc.abstractmethod
    def firmar_y_enviar_nota_debito(self, nota_data: dict) -> DianResponse:
        """Firma y envía una Nota de Débito electrónica."""
        ...

    @abc.abstractmethod
    def consultar_estado(self, cufe: str) -> DianResponse:
        """Consulta el estado de un documento ya enviado."""
        ...


class DianDummyAdapter(DianAdapterBase):
    """
    Adaptador de pruebas/desarrollo para simular la comunicación con la DIAN.

    Genera CUFEs ficticios y respuestas exitosas sin conectarse a ningún
    servicio externo. Utilizar exclusivamente en ambientes de desarrollo
    y pruebas automatizadas.

    Para producción, reemplazar por el adaptador del proveedor certificado.
    """

    def firmar_y_enviar_factura(self, factura_data: dict) -> DianResponse:
        cufe = f"CUFE-DEV-{uuid.uuid4().hex[:16].upper()}"
        logger.info(f"[DIAN DUMMY] Factura simulada enviada. CUFE: {cufe}")
        return DianResponse(
            exitoso=True,
            cufe=cufe,
            qr_code=f"https://catalogo-vpfe.dian.gov.co/document/{cufe}",
            xml_firmado="<xml>dummy_signed</xml>",
            mensaje="Documento aceptado por la DIAN (ambiente de pruebas).",
            codigo_respuesta="00",
            fecha_validacion=datetime.now()
        )

    def firmar_y_enviar_nota_credito(self, nota_data: dict) -> DianResponse:
        cufe = f"CUFE-NC-DEV-{uuid.uuid4().hex[:16].upper()}"
        logger.info(f"[DIAN DUMMY] Nota Crédito simulada. CUFE: {cufe}")
        return DianResponse(
            exitoso=True,
            cufe=cufe,
            qr_code=f"https://catalogo-vpfe.dian.gov.co/document/{cufe}",
            xml_firmado="<xml>dummy_nc_signed</xml>",
            mensaje="Nota de Crédito aceptada (ambiente de pruebas).",
            codigo_respuesta="00",
            fecha_validacion=datetime.now()
        )

    def firmar_y_enviar_nota_debito(self, nota_data: dict) -> DianResponse:
        cufe = f"CUFE-ND-DEV-{uuid.uuid4().hex[:16].upper()}"
        logger.info(f"[DIAN DUMMY] Nota Débito simulada. CUFE: {cufe}")
        return DianResponse(
            exitoso=True,
            cufe=cufe,
            qr_code=f"https://catalogo-vpfe.dian.gov.co/document/{cufe}",
            xml_firmado="<xml>dummy_nd_signed</xml>",
            mensaje="Nota de Débito aceptada (ambiente de pruebas).",
            codigo_respuesta="00",
            fecha_validacion=datetime.now()
        )

    def consultar_estado(self, cufe: str) -> DianResponse:
        logger.info(f"[DIAN DUMMY] Consulta de estado para CUFE: {cufe}")
        return DianResponse(
            exitoso=True,
            cufe=cufe,
            mensaje="Documento validado exitosamente (ambiente de pruebas).",
            codigo_respuesta="00",
            fecha_validacion=datetime.now()
        )


class DianService:
    """
    Servicio de Facturación Electrónica.

    Actúa como fachada que delega al adaptador configurado. Por defecto
    usa DianDummyAdapter. Para producción, inyectar el adaptador real
    del proveedor certificado.

    Uso:
        service = DianService()  # Usa DianDummyAdapter por defecto
        service = DianService(adapter=CarvajalAdapter())  # Producción
    """

    def __init__(self, adapter: Optional[DianAdapterBase] = None):
        self._adapter = adapter or DianDummyAdapter()

    def enviar_factura(self, factura) -> DianResponse:
        """Prepara los datos de la factura y los envía al adaptador DIAN."""
        factura_data = {
            "numero": factura.numero,
            "fecha_emision": str(factura.fecha_emision),
            "cliente_nombre": factura.cliente.nombre,
            "cliente_documento": factura.cliente.numero_documento,
            "subtotal": str(factura.subtotal),
            "impuestos": str(factura.impuestos_total),
            "total": str(factura.total),
            "detalles": [
                {
                    "producto": d.producto.nombre,
                    "cantidad": str(d.cantidad),
                    "precio_unitario": str(d.precio_unitario),
                    "total_linea": str(d.total_linea),
                }
                for d in factura.detalles.select_related('producto').all()
            ]
        }
        return self._adapter.firmar_y_enviar_factura(factura_data)

    def enviar_nota_credito(self, nota_credito) -> DianResponse:
        """Prepara y envía una Nota de Crédito al adaptador DIAN."""
        nota_data = {
            "numero": nota_credito.numero,
            "factura_referencia": nota_credito.factura.numero,
            "motivo": nota_credito.motivo,
            "total": str(nota_credito.total),
            "detalles": [
                {
                    "producto": d.producto_nombre,
                    "cantidad": str(d.cantidad),
                    "precio_unitario": str(d.precio_unitario),
                    "subtotal": str(d.subtotal),
                }
                for d in nota_credito.detalles.all()
            ]
        }
        return self._adapter.firmar_y_enviar_nota_credito(nota_data)

    def enviar_nota_debito(self, nota_debito) -> DianResponse:
        """Prepara y envía una Nota de Débito al adaptador DIAN."""
        nota_data = {
            "numero": nota_debito.numero,
            "factura_referencia": nota_debito.factura.numero,
            "motivo": nota_debito.motivo,
            "total": str(nota_debito.total),
            "detalles": [
                {
                    "producto": d.producto_nombre,
                    "cantidad": str(d.cantidad),
                    "precio_unitario": str(d.precio_unitario),
                    "subtotal": str(d.subtotal),
                }
                for d in nota_debito.detalles.all()
            ]
        }
        return self._adapter.firmar_y_enviar_nota_debito(nota_data)

    def consultar_estado(self, cufe: str) -> DianResponse:
        """Consulta el estado de un documento por su CUFE."""
        return self._adapter.consultar_estado(cufe)
