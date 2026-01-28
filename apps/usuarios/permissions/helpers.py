def tiene_rol(usuario, rol):
    return (
        usuario.is_authenticated and
        usuario.usuario_roles.filter(rol__nombre=rol).exists()
    )


def tiene_alguno_de_estos_roles(usuario, roles):
    return (
        usuario.is_authenticated and
        usuario.usuario_roles.filter(rol__nombre__in=roles).exists()
    )


def obtener_roles_usuario(usuario):
    if not usuario.is_authenticated:
        return []

    return list(
        usuario.usuario_roles.values_list('rol__nombre', flat=True)
    )


def es_administrador(usuario):
    return tiene_rol(usuario, 'Administrador')


def es_supervisor_o_superior(usuario):
    return tiene_alguno_de_estos_roles(usuario, ['Supervisor', 'Administrador'])
