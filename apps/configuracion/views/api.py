# apps/configuracion/views/api.py
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    VISTAS API - APP CONFIGURACIÓN                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

¿Por qué usamos APIView y no ModelViewSet aquí?
-------------------------------------------------
En las otras apps (ventas, inventario) usamos ModelViewSet porque manejamos
listas de muchos objetos (muchas ventas, muchos productos).

La Configuración es diferente:
- Solo existe UN registro (Singleton)
- No tiene lista, ni paginación, ni eliminación
- Las acciones son: ver, actualizar, y acciones específicas

Por eso usamos APIView que nos da más control sobre los endpoints.

Endpoints:
    GET  /api/configuracion/                → Ver configuración actual
    PUT  /api/configuracion/               → Actualizar toda la configuración
    PATCH /api/configuracion/              → Actualizar campos específicos
    POST /api/configuracion/reset-consecutivo/  → Resetear un consecutivo
    GET  /api/configuracion/empresa/       → Info resumida de la empresa

Permisos:
    - Ver (GET):       Cualquier usuario autenticado
    - Actualizar:      Solo Administrador
    - Reset:           Solo Administrador

Autor: Sistema ERP
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.configuracion.models import ConfiguracionGeneral
from apps.configuracion.services import ConfiguracionService
from apps.configuracion.serializers import (
    ConfiguracionReadSerializer,
    ConfiguracionResumenSerializer,
    ConfiguracionUpdateSerializer,
    ResetConsecutivoSerializer,
)
from apps.usuarios.permissions import EsAdministrador
from apps.auditorias.services.auditoria_service import AuditoriaService


# ============================================================================
# VISTA PRINCIPAL DE CONFIGURACIÓN
# ============================================================================


class ConfiguracionView(APIView):
    """
    Vista para GET, PUT y PATCH de la configuración general.

    ¿Qué es APIView?
    ----------------
    APIView es la vista base de DRF. A diferencia de ModelViewSet,
    aquí definimos manualmente qué hace cada método HTTP:
    - def get(...)   → responde a GET
    - def put(...)   → responde a PUT
    - def patch(...) → responde a PATCH

    Parser classes:
    ---------------
    Necesitamos MultiPartParser y FormParser para permitir subir el logo
    (archivos binarios). JSONParser para datos normales en JSON.
    """

    # Parsers que acepta esta vista
    # MultiPartParser: para formularios con archivos (subir logo)
    # FormParser: para formularios sin archivos
    # JSONParser: para JSON normal sin archivos
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        """
        Permisos dinámicos según el método HTTP.

        ¿Por qué dinámicos?
        - GET: cualquier usuario autenticado puede VER la configuración
        - PUT/PATCH: solo el administrador puede MODIFICAR la configuración

        get_permissions() es un método de APIView que retorna la lista
        de clases de permisos a aplicar según la request actual.
        """
        if self.request.method in ["PUT", "PATCH"]:
            return [IsAuthenticated(), EsAdministrador()]
        return [IsAuthenticated()]

    def get(self, request):
        """
        GET /api/configuracion/
        Retorna la configuración actual del sistema.

        Respuesta:
            200 OK con todos los datos de configuración
        """
        config = ConfiguracionService.obtener_configuracion()

        # Pasamos 'request' al contexto del serializer para que
        # get_logo_url() pueda construir la URL completa del logo
        serializer = ConfiguracionReadSerializer(config, context={"request": request})

        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """
        PUT /api/configuracion/
        Actualización COMPLETA de la configuración.

        PUT envía todos los campos del formulario.
        Si falta algún campo requerido, da error de validación.

        Proceso:
        1. Validar los datos con el serializer
        2. Llamar al servicio para actualizar
        3. Retornar los datos actualizados con el serializer de lectura
        """
        config = ConfiguracionService.obtener_configuracion()

        serializer = ConfiguracionUpdateSerializer(
            config,
            data=request.data,
            partial=False,  # PUT = actualización completa
        )

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        config_actualizada = ConfiguracionService.actualizar_configuracion(
            serializer.validated_data
        )

        # Auditoría
        AuditoriaService.registrar_accion(
            usuario=request.user,
            accion='ACTUALIZAR',
            modulo='SISTEMA',
            objeto=config_actualizada,
            descripcion="Configuración general actualizada (Sincronización completa)",
            request=request
        )

        # Respondemos con el serializer de LECTURA (no el de escritura)
        # para que el frontend reciba todos los datos enriquecidos
        response_serializer = ConfiguracionReadSerializer(
            config_actualizada, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        """
        PATCH /api/configuracion/
        Actualización PARCIAL de la configuración.

        PATCH envía solo los campos que quieren cambiar.
        Útil para: "solo quiero cambiar el teléfono" sin enviar todo el formulario.

        La diferencia con PUT es partial=True en el serializer.
        Con partial=True, los campos requeridos del modelo no son obligatorios
        en la request si no se están modificando.
        """
        config = ConfiguracionService.obtener_configuracion()

        serializer = ConfiguracionUpdateSerializer(
            config,
            data=request.data,
            partial=True,  # PATCH = actualización parcial (solo campos enviados)
        )

        if not serializer.is_valid():
            print("Errores del serializer:")
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        config_actualizada = ConfiguracionService.actualizar_configuracion(
            serializer.validated_data
        )

        # Auditoría
        AuditoriaService.registrar_accion(
            usuario=request.user,
            accion='ACTUALIZAR',
            modulo='SISTEMA',
            objeto=config_actualizada,
            descripcion="Configuración general actualizada (Cambios parciales)",
            request=request
        )

        response_serializer = ConfiguracionReadSerializer(
            config_actualizada, context={"request": request}
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)


# ============================================================================
# VISTA PARA RESETEAR CONSECUTIVOS
# ============================================================================


class ResetConsecutivoView(APIView):
    """
    POST /api/configuracion/reset-consecutivo/
    Resetea o ajusta el consecutivo de un tipo de documento.

    ⚠️ ACCIÓN CRÍTICA: Solo Administrador puede hacerlo.
    Requiere confirmación explícita.

    Ejemplo de body:
        {
            "tipo": "factura",
            "nuevo_consecutivo": 1,
            "confirmar": true
        }
    """

    permission_classes = [IsAuthenticated, EsAdministrador]

    def post(self, request):
        """
        Procesa el reset del consecutivo.

        Proceso:
        1. Validar los datos (tipo, nuevo_consecutivo, confirmar)
        2. Llamar al servicio para hacer el cambio
        3. Retornar la configuración actualizada
        """
        serializer = ResetConsecutivoSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        tipo = serializer.validated_data["tipo"]
        nuevo_consecutivo = serializer.validated_data["nuevo_consecutivo"]

        try:
            config = ConfiguracionService.reset_consecutivo(tipo, nuevo_consecutivo)
            
            # Auditoría
            AuditoriaService.registrar_accion(
                usuario=request.user,
                accion='ACTUALIZAR',
                modulo='SISTEMA',
                objeto=config,
                descripcion=f"Reinicio de consecutivo: {tipo} a {nuevo_consecutivo}",
                request=request
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ConfiguracionReadSerializer(
            config, context={"request": request}
        )
        return Response(
            {
                "mensaje": f"Consecutivo de {tipo} actualizado a {nuevo_consecutivo} exitosamente.",
                "configuracion": response_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


# ============================================================================
# VISTA PÚBLICA: INFO EMPRESA
# ============================================================================


class InfoEmpresaView(APIView):
    """
    GET /api/configuracion/empresa/
    Retorna el resumen de información de la empresa.

    ¿Para qué sirve este endpoint?
    - El frontend lo usa para mostrar el nombre y logo en el header
    - Los reportes y PDFs lo usan para el encabezado
    - Es un endpoint liviano (menos datos que la config completa)

    Permisos: Solo usuarios autenticados (cualquier rol)
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        config = ConfiguracionService.obtener_configuracion()
        serializer = ConfiguracionResumenSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)
