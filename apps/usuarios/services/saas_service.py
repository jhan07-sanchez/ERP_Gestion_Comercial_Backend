# apps/usuarios/services/saas_service.py
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
from apps.usuarios.models import Usuario, Empresa, Suscripcion, SolicitudCuenta, Rol, UsuarioRol, TokenActivacion, Plan

class SaaSAccountService:
    """Servicio para gestionar el ciclo de vida de cuentas SaaS (Solicitudes, Trial, etc.)"""

    @staticmethod
    @transaction.atomic
    def aprobar_solicitud(solicitud_id):
        """
        Aprueba una solicitud de cuenta:
        1. Crea la Empresa
        2. Crea el Usuario administrador (is_active=False, unusable password)
        3. Crea la Suscripción Inactiva (sin trial iniciado)
        4. Crea el TokenActivacion
        5. Cambia estado de solicitud a APROBADA
        6. Envía correo con link de activación
        """
        solicitud = SolicitudCuenta.objects.select_for_update().get(id=solicitud_id)
        
        if solicitud.estado != 'PENDIENTE':
            raise ValueError(f"La solicitud ya se encuentra en estado {solicitud.estado}")

        # 1. Crear Empresa
        empresa = Empresa.objects.create(nombre=solicitud.empresa)

        # 2. Crear Usuario (Admin de la empresa, inactivo y sin password)
        rol_admin, _ = Rol.objects.get_or_create(nombre='ADMINISTRADOR', defaults={'descripcion': 'Admin total de la empresa'})
        
        usuario = Usuario.objects.create(
            username=solicitud.email,
            email=solicitud.email,
            empresa=empresa,
            is_active=False
        )
        usuario.set_unusable_password()
        usuario.save()
        
        UsuarioRol.objects.create(usuario=usuario, rol=rol_admin)

        # 3. Buscar el Plan y Crear Suscripción Inactiva
        try:
            plan_obj = Plan.objects.get(nombre=solicitud.plan)
        except Plan.DoesNotExist:
            raise ValueError(f"El plan '{solicitud.plan}' no existe en el sistema.")

        Suscripcion.objects.create(
            empresa=empresa,
            plan=plan_obj,
            es_trial=True,
            fecha_inicio=None,
            fecha_fin=None,
            activa=False
        )

        # 4. Crear Token de Activación
        token = TokenActivacion.objects.create(usuario=usuario)

        # 5. Actualizar Solicitud
        solicitud.estado = 'APROBADA'
        solicitud.save()

        # 6. Enviar correo de activación
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
        link_activacion = f"{frontend_url}/activar-cuenta?token={token.token}"
        
        try:
            send_mail(
                subject='Tu cuenta ha sido aprobada - Activa tu acceso',
                message=f'Hola,\n\nTu solicitud de cuenta para {solicitud.empresa} ha sido aprobada.\n'
                        f'Por favor, activa tu cuenta y establece tu contraseña haciendo clic en el siguiente enlace '
                        f'(válido por 24 horas):\n\n{link_activacion}\n\n'
                        f'Tu período de prueba de 7 días comenzará en el momento en que actives la cuenta.\n\n'
                        f'Saludos,\nEl equipo SaaS',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@midominio.com'),
                recipient_list=[solicitud.email],
                fail_silently=True,
            )
        except Exception as e:
            # Podríamos loguear el error, pero no fallamos la transacción
            print(f"Error al enviar correo de activación: {e}")

        return usuario, empresa

    @staticmethod
    @transaction.atomic
    def activar_cuenta(token_uuid, new_password):
        """
        Activa una cuenta previamente aprobada:
        1. Valida el token
        2. Establece la contraseña y activa el usuario
        3. Marca el token como usado
        4. Inicia el período de prueba de la suscripción (7 días)
        """
        try:
            token = TokenActivacion.objects.select_related('usuario__empresa__suscripcion').get(token=token_uuid)
        except TokenActivacion.DoesNotExist:
            raise ValueError("Token de activación inválido.")

        if not token.es_valido():
            raise ValueError("El token de activación ha expirado o ya fue usado.")

        usuario = token.usuario
        suscripcion = usuario.empresa.suscripcion

        # 1. Activar usuario y setear password
        usuario.set_password(new_password)
        usuario.is_active = True
        usuario.save()

        # 2. Marcar token como usado
        token.usado = True
        token.save()

        # 3. Iniciar Trial de 7 días
        suscripcion.fecha_inicio = timezone.now()
        suscripcion.fecha_fin = timezone.now() + timedelta(days=7)
        suscripcion.activa = True
        suscripcion.save()
        
        # 4. Enviar correo de bienvenida (opcional)
        try:
            send_mail(
                subject='Bienvenido a nuestra plataforma',
                message=f'Hola {usuario.username},\n\n'
                        f'Tu cuenta ha sido activada exitosamente.\n'
                        f'Tu período de prueba de 7 días ha comenzado y finalizará el {suscripcion.fecha_fin.strftime("%d/%m/%Y")}.\n\n'
                        f'Saludos,\nEl equipo SaaS',
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@midominio.com'),
                recipient_list=[usuario.email],
                fail_silently=True,
            )
        except Exception as e:
            print(f"Error al enviar correo de bienvenida: {e}")

        return usuario
