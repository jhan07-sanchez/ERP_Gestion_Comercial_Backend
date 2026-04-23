from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
import uuid
from datetime import timedelta

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre


class Empresa(models.Model):
    nombre = models.CharField(max_length=200)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'empresas'
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('El email es obligatorio')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(email, username, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, null=True, blank=True, related_name='usuarios')
    token = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Retorna el nombre completo o el username si no tiene."""
        return self.username

    def get_short_name(self):
        """Retorna el nombre corto o el username."""
        return self.username


class UsuarioRol(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='usuario_roles')
    rol = models.ForeignKey(Rol, on_delete=models.CASCADE, related_name='usuario_roles')

    class Meta:
        db_table = 'usuario_rol'
        unique_together = ('usuario', 'rol')
        verbose_name = 'Usuario Rol'
        verbose_name_plural = 'Usuario Roles'

    def __str__(self):
        return f"{self.usuario.username} - {self.rol.nombre}"


class SolicitudCuenta(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
    ]
    nombre = models.CharField(max_length=150)
    empresa = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=50)
    plan = models.CharField(max_length=50)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'solicitudes_cuenta'
        verbose_name = 'Solicitud de Cuenta'
        verbose_name_plural = 'Solicitudes de Cuenta'

    def __str__(self):
        return f"{self.empresa} - {self.email}"


class Modulo(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.SlugField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'modulos'
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'

    def __str__(self):
        return self.nombre


class Plan(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    modulos = models.ManyToManyField(Modulo, related_name='planes', blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'planes'
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'

    def __str__(self):
        return self.nombre


class Suscripcion(models.Model):
    ESTADOS_PAGO = [
        ('activa', 'Activa'),
        ('cancelada', 'Cancelada'),
        ('en_gracia', 'En período de gracia'),
    ]

    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='suscripcion')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='suscripciones')
    es_trial = models.BooleanField(default=True)
    fecha_inicio = models.DateTimeField(null=True, blank=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    activa = models.BooleanField(default=False)
    
    # Preparación para pagos
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='activa')

    class Meta:
        db_table = 'suscripciones'
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'

    def __str__(self):
        return f"{self.empresa.nombre} - {self.plan.nombre}"

    def esta_activa(self):
        if not self.activa:
            return False
        if self.fecha_fin:
            return self.fecha_fin >= timezone.now()
        return False

    def dias_restantes(self):
        if self.fecha_fin:
            return (self.fecha_fin - timezone.now()).days
        return 0


class TokenActivacion(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name='token_activacion')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tokens_activacion'
        verbose_name = 'Token de Activación'
        verbose_name_plural = 'Tokens de Activación'

    def __str__(self):
        return str(self.token)

    def es_valido(self):
        """El token es válido si no se ha usado y tiene menos de 24 horas."""
        if self.usado:
            return False
        # Calcular si han pasado menos de 24 horas (86400 segundos)
        return (timezone.now() - self.creado_en).total_seconds() < 86400