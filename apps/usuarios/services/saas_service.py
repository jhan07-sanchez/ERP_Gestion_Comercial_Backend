# apps/usuarios/services/saas_service.py
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth.models import Group
from apps.usuarios.models import Usuario, Empresa, Suscripcion, SolicitudCuenta, Rol, UsuarioRol

class SaaSAccountService:
    """Servicio para gestionar el ciclo de vida de cuentas SaaS (Solicitudes, Trial, etc.)"""

    @staticmethod
    @transaction.atomic
    def aprobar_solicitud(solicitud_id, password_temporal="Temporal123*"):
        """
        Aprueba una solicitud de cuenta:
        1. Crea la Empresa
        2. Crea el Usuario administrador de esa empresa
        3. Crea la Suscripción Trial (7 días)
        4. Cambia estado de solicitud a APROBADA
        """
        solicitud = SolicitudCuenta.objects.get(id=solicitud_id)
        
        if solicitud.estado != 'PENDIENTE':
            raise ValueError(f"La solicitud ya se encuentra en estado {solicitud.estado}")

        # 1. Crear Empresa
        empresa = Empresa.objects.create(nombre=solicitud.empresa)

        # 2. Crear Usuario (Admin de la empresa)
        # Buscamos o creamos el rol ADMIN si no existe
        rol_admin, _ = Rol.objects.get_or_create(nombre='ADMINISTRADOR', defaults={'descripcion': 'Admin total de la empresa'})
        
        usuario = Usuario.objects.create_user(
            username=solicitud.email, # Usamos email como username por practicidad en el registro
            email=solicitud.email,
            password=password_temporal,
            empresa=empresa
        )
        
        # Asignar rol
        UsuarioRol.objects.create(usuario=usuario, rol=rol_admin)

        # 3. Crear Suscripción Trial
        fecha_inicio = timezone.now()
        fecha_fin = fecha_inicio + timedelta(days=7)
        
        Suscripcion.objects.create(
            empresa=empresa,
            plan=solicitud.plan, # O forzar 'PRO' según instrucciones: "plan = 'PRO'"
            es_trial=True,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            activa=True
        )

        # 4. Actualizar Solicitud
        solicitud.estado = 'APROBADA'
        solicitud.save()

        return usuario, empresa
