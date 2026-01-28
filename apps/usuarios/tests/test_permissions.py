# apps/usuarios/tests/test_permissions.py

"""
Tests para el sistema de permisos basado en roles.

Este archivo contiene tests completos que verifican que los permisos
funcionan correctamente para cada rol del sistema.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from apps.usuarios.models import Usuario, Rol, UsuarioRol
from apps.usuarios.permissions import (
    EsAdministrador,
    EsSupervisor,
    EsVendedor,
    EsCajero,
    EsAlmacenista,
    tiene_rol,
    tiene_alguno_de_estos_roles,
    obtener_roles_usuario,
    es_administrador,
    es_supervisor_o_superior
)


# ============================================================================
# TESTS DE FUNCIONES AUXILIARES
# ============================================================================

class FuncionesAuxiliaresTest(TestCase):
    """Tests para funciones auxiliares de permisos"""
    
    def setUp(self):
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.rol_vendedor = Rol.objects.create(nombre='Vendedor')
        
        # Crear usuario con rol
        self.usuario = Usuario.objects.create_user(
            username='test',
            email='test@test.com',
            password='pass123'
        )
        UsuarioRol.objects.create(usuario=self.usuario, rol=self.rol_admin)
        UsuarioRol.objects.create(usuario=self.usuario, rol=self.rol_vendedor)
    
    def test_tiene_rol(self):
        """Test: tiene_rol() funciona correctamente"""
        self.assertTrue(tiene_rol(self.usuario, 'Administrador'))
        self.assertTrue(tiene_rol(self.usuario, 'Vendedor'))
        self.assertFalse(tiene_rol(self.usuario, 'Cajero'))
    
    def test_tiene_alguno_de_estos_roles(self):
        """Test: tiene_alguno_de_estos_roles() funciona"""
        self.assertTrue(
            tiene_alguno_de_estos_roles(self.usuario, ['Administrador', 'Supervisor'])
        )
        self.assertTrue(
            tiene_alguno_de_estos_roles(self.usuario, ['Vendedor'])
        )
        self.assertFalse(
            tiene_alguno_de_estos_roles(self.usuario, ['Cajero', 'Almacenista'])
        )
    
    def test_obtener_roles_usuario(self):
        """Test: obtener_roles_usuario() retorna lista correcta"""
        roles = obtener_roles_usuario(self.usuario)
        self.assertEqual(len(roles), 2)
        self.assertIn('Administrador', roles)
        self.assertIn('Vendedor', roles)
    
    def test_es_administrador(self):
        """Test: es_administrador() funciona"""
        self.assertTrue(es_administrador(self.usuario))
        
        # Usuario sin rol admin
        usuario2 = Usuario.objects.create_user(
            username='test2',
            email='test2@test.com',
            password='pass123'
        )
        self.assertFalse(es_administrador(usuario2))
    
    def test_es_supervisor_o_superior(self):
        """Test: es_supervisor_o_superior() funciona"""
        self.assertTrue(es_supervisor_o_superior(self.usuario))
        
        # Crear supervisor
        rol_super = Rol.objects.create(nombre='Supervisor')
        usuario2 = Usuario.objects.create_user(
            username='super',
            email='super@test.com',
            password='pass123'
        )
        UsuarioRol.objects.create(usuario=usuario2, rol=rol_super)
        self.assertTrue(es_supervisor_o_superior(usuario2))


# ============================================================================
# TESTS DE PERMISOS BÁSICOS
# ============================================================================

class PermisosBasicosTest(APITestCase):
    """Tests para permisos básicos por rol"""
    
    def setUp(self):
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.rol_supervisor = Rol.objects.create(nombre='Supervisor')
        self.rol_vendedor = Rol.objects.create(nombre='Vendedor')
        self.rol_cajero = Rol.objects.create(nombre='Cajero')
        self.rol_almacenista = Rol.objects.create(nombre='Almacenista')
        
        # Crear usuarios
        self.admin = self._crear_usuario('admin', 'admin@test.com', self.rol_admin)
        self.supervisor = self._crear_usuario('super', 'super@test.com', self.rol_supervisor)
        self.vendedor = self._crear_usuario('vend', 'vend@test.com', self.rol_vendedor)
        self.cajero = self._crear_usuario('caj', 'caj@test.com', self.rol_cajero)
        self.almacenista = self._crear_usuario('alm', 'alm@test.com', self.rol_almacenista)
        self.sin_rol = self._crear_usuario('sinrol', 'sinrol@test.com', None)
        
        self.client = APIClient()
    
    def _crear_usuario(self, username, email, rol=None):
        """Helper: Crear usuario con rol"""
        usuario = Usuario.objects.create_user(
            username=username,
            email=email,
            password='pass123'
        )
        if rol:
            UsuarioRol.objects.create(usuario=usuario, rol=rol)
        return usuario
    
    def test_admin_tiene_acceso_total(self):
        """Test: Administrador tiene acceso a todo"""
        self.assertTrue(tiene_rol(self.admin, 'Administrador'))
        self.assertTrue(es_administrador(self.admin))
    
    def test_supervisor_es_superior(self):
        """Test: Supervisor es considerado superior"""
        self.assertTrue(es_supervisor_o_superior(self.supervisor))
        self.assertTrue(tiene_rol(self.supervisor, 'Supervisor'))
    
    def test_vendedor_no_es_superior(self):
        """Test: Vendedor no es superior"""
        self.assertFalse(es_supervisor_o_superior(self.vendedor))
        self.assertTrue(tiene_rol(self.vendedor, 'Vendedor'))
    
    def test_usuario_sin_rol_no_tiene_permisos(self):
        """Test: Usuario sin rol no tiene ningún permiso"""
        self.assertFalse(tiene_alguno_de_estos_roles(
            self.sin_rol,
            ['Administrador', 'Supervisor', 'Vendedor', 'Cajero', 'Almacenista']
        ))


# ============================================================================
# TESTS DE ENDPOINTS CON PERMISOS
# ============================================================================

class PermisosUsuariosAPITest(APITestCase):
    """Tests de permisos en endpoints de usuarios"""
    
    def setUp(self):
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.rol_vendedor = Rol.objects.create(nombre='Vendedor')
        
        # Crear usuarios
        self.admin = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        UsuarioRol.objects.create(usuario=self.admin, rol=self.rol_admin)
        
        self.vendedor = Usuario.objects.create_user(
            username='vendedor',
            email='vendedor@test.com',
            password='vend123'
        )
        UsuarioRol.objects.create(usuario=self.vendedor, rol=self.rol_vendedor)
        
        self.sin_rol = Usuario.objects.create_user(
            username='sinrol',
            email='sinrol@test.com',
            password='sinrol123'
        )
        
        self.client = APIClient()
        self.list_url = reverse('usuarios:usuario-list')
    
    def test_admin_puede_listar_usuarios(self):
        """Test: Admin puede listar usuarios"""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_vendedor_no_puede_listar_usuarios(self):
        """Test: Vendedor no puede listar todos los usuarios"""
        self.client.force_authenticate(user=self.vendedor)
        response = self.client.get(self.list_url)
        
        # Debería poder ver, pero solo a sí mismo
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que solo ve 1 usuario (él mismo)
        self.assertEqual(response.data['count'], 1)
    
    def test_admin_puede_crear_usuario(self):
        """Test: Admin puede crear usuarios"""
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password': 'nuevo123',
            'password2': 'nuevo123'
        }
        
        response = self.client.post(self.list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_vendedor_no_puede_crear_usuario(self):
        """Test: Vendedor no puede crear usuarios"""
        self.client.force_authenticate(user=self.vendedor)
        
        data = {
            'username': 'nuevo',
            'email': 'nuevo@test.com',
            'password': 'nuevo123',
            'password2': 'nuevo123'
        }
        
        response = self.client.post(self.list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PermisosRolesAPITest(APITestCase):
    """Tests de permisos en endpoints de roles"""
    
    def setUp(self):
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.rol_vendedor = Rol.objects.create(nombre='Vendedor')
        
        # Crear usuarios
        self.admin = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        UsuarioRol.objects.create(usuario=self.admin, rol=self.rol_admin)
        
        self.vendedor = Usuario.objects.create_user(
            username='vendedor',
            email='vendedor@test.com',
            password='vend123'
        )
        UsuarioRol.objects.create(usuario=self.vendedor, rol=self.rol_vendedor)
        
        self.client = APIClient()
        self.list_url = reverse('usuarios:rol-list')
    
    def test_admin_puede_gestionar_roles(self):
        """Test: Admin puede crear roles"""
        self.client.force_authenticate(user=self.admin)
        
        data = {
            'nombre': 'Nuevo Rol',
            'descripcion': 'Descripción del rol'
        }
        
        response = self.client.post(self.list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_vendedor_no_puede_crear_roles(self):
        """Test: Vendedor no puede crear roles"""
        self.client.force_authenticate(user=self.vendedor)
        
        data = {
            'nombre': 'Nuevo Rol',
            'descripcion': 'Descripción del rol'
        }
        
        response = self.client.post(self.list_url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ============================================================================
# TESTS DE PERMISOS A NIVEL DE OBJETO
# ============================================================================

class PermisosObjetoTest(TestCase):
    """Tests para permisos a nivel de objeto"""
    
    def setUp(self):
        # Crear roles
        self.rol_admin = Rol.objects.create(nombre='Administrador')
        self.rol_vendedor = Rol.objects.create(nombre='Vendedor')
        
        # Crear usuarios
        self.admin = Usuario.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        UsuarioRol.objects.create(usuario=self.admin, rol=self.rol_admin)
        
        self.vendedor1 = Usuario.objects.create_user(
            username='vendedor1',
            email='vendedor1@test.com',
            password='vend123'
        )
        UsuarioRol.objects.create(usuario=self.vendedor1, rol=self.rol_vendedor)
        
        self.vendedor2 = Usuario.objects.create_user(
            username='vendedor2',
            email='vendedor2@test.com',
            password='vend123'
        )
        UsuarioRol.objects.create(usuario=self.vendedor2, rol=self.rol_vendedor)
    
    def test_usuario_puede_editar_su_perfil(self):
        """Test: Usuario puede editar su propio perfil"""
        from apps.usuarios.permissions import PuedeEditarPropio
        from unittest.mock import Mock
        
        permission = PuedeEditarPropio()
        request = Mock(user=self.vendedor1, method='PUT')
        view = Mock()
        
        # El vendedor1 editando su propio perfil
        self.assertTrue(
            permission.has_object_permission(request, view, self.vendedor1)
        )
    
    def test_usuario_no_puede_editar_otro_perfil(self):
        """Test: Usuario no puede editar perfil de otro"""
        from apps.usuarios.permissions import PuedeEditarPropio
        from unittest.mock import Mock
        
        permission = PuedeEditarPropio()
        request = Mock(user=self.vendedor1, method='PUT')
        view = Mock()
        
        # El vendedor1 intentando editar perfil de vendedor2
        self.assertFalse(
            permission.has_object_permission(request, view, self.vendedor2)
        )
    
    def test_admin_puede_editar_cualquier_perfil(self):
        """Test: Admin puede editar cualquier perfil"""
        from apps.usuarios.permissions import PuedeEditarPropio
        from unittest.mock import Mock
        
        permission = PuedeEditarPropio()
        request = Mock(user=self.admin, method='PUT')
        view = Mock()
        
        # Admin editando perfil de vendedor1
        self.assertTrue(
            permission.has_object_permission(request, view, self.vendedor1)
        )


# ============================================================================
# TESTS DE INTEGRACIÓN COMPLETA
# ============================================================================

class IntegracionPermisosTest(APITestCase):
    """Tests de integración del sistema completo de permisos"""
    
    def setUp(self):
        # Crear todos los roles
        self.roles = {
            'admin': Rol.objects.create(nombre='Administrador'),
            'supervisor': Rol.objects.create(nombre='Supervisor'),
            'vendedor': Rol.objects.create(nombre='Vendedor'),
            'cajero': Rol.objects.create(nombre='Cajero'),
            'almacenista': Rol.objects.create(nombre='Almacenista'),
        }
        
        # Crear usuarios con cada rol
        self.usuarios = {}
        for rol_nombre, rol in self.roles.items():
            usuario = Usuario.objects.create_user(
                username=rol_nombre,
                email=f'{rol_nombre}@test.com',
                password='pass123'
            )
            UsuarioRol.objects.create(usuario=usuario, rol=rol)
            self.usuarios[rol_nombre] = usuario
        
        self.client = APIClient()
    
    def test_flujo_completo_vendedor(self):
        """Test: Flujo completo de un vendedor"""
        vendedor = self.usuarios['vendedor']
        self.client.force_authenticate(user=vendedor)
        
        # 1. Puede ver usuarios (solo él mismo)
        response = self.client.get(reverse('usuarios:usuario-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        
        # 2. Puede ver su propio perfil
        response = self.client.get(reverse('usuarios:usuario-me'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'vendedor')
        
        # 3. No puede crear usuarios
        response = self.client.post(
            reverse('usuarios:usuario-list'),
            {'username': 'nuevo', 'email': 'nuevo@test.com', 'password': 'pass', 'password2': 'pass'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_flujo_completo_admin(self):
        """Test: Flujo completo de un administrador"""
        admin = self.usuarios['admin']
        self.client.force_authenticate(user=admin)
        
        # 1. Puede ver todos los usuarios
        response = self.client.get(reverse('usuarios:usuario-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data['count'], 5)
        
        # 2. Puede crear roles
        response = self.client.post(
            reverse('usuarios:rol-list'),
            {'nombre': 'Test Rol', 'descripcion': 'Test'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 3. Puede asignar roles
        vendedor = self.usuarios['vendedor']
        nuevo_rol = Rol.objects.get(nombre='Test Rol')
        
        response = self.client.post(
            reverse('usuarios:usuario-asignar-rol', kwargs={'pk': vendedor.id}),
            {'rol_id': nuevo_rol.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# ============================================================================
# EJECUTAR TODOS LOS TESTS
# ============================================================================

"""
Para ejecutar estos tests:

# Todos los tests de permisos
python manage.py test apps.usuarios.tests.test_permissions

# Un test específico
python manage.py test apps.usuarios.tests.test_permissions.FuncionesAuxiliaresTest.test_tiene_rol

# Con verbosidad
python manage.py test apps.usuarios.tests.test_permissions --verbosity=2

# Con cobertura
coverage run --source='apps.usuarios' manage.py test apps.usuarios.tests.test_permissions
coverage report
"""