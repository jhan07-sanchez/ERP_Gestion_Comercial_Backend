# apps/documentos/exceptions.py
"""
Excepciones personalizadas del módulo Documentos ERP.

Jerarquía:
    DocumentoError (base)
    ├── DocumentoYaExisteError   → duplicado
    ├── DocumentoAnulacionError  → regla de anulación
    ├── NumeracionError          → fallo de secuencia
    └── DocumentoValidacionError → full_clean falló
"""


class DocumentoError(Exception):
    """Error base del módulo documentos."""
    pass


class DocumentoYaExisteError(DocumentoError):
    """Se intentó crear un documento duplicado para la misma operación."""
    pass


class DocumentoAnulacionError(DocumentoError):
    """Error al anular un documento (ya anulado, regla de negocio, etc.)."""
    pass


class NumeracionError(DocumentoError):
    """Error en la generación de números secuenciales de documento."""
    pass


class DocumentoValidacionError(DocumentoError):
    """El documento no pasó full_clean() antes de persistirse."""
    pass
