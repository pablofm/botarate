def es_administración(usuario):
    """Administración (staff o superusuarios), por oposición al profesorado."""
    return usuario.is_staff or usuario.is_superuser


def es_staff(usuario):
    """Solo el staff, sin contar a los superusuarios que no lo sean: es quien lleva las ventas."""
    return usuario.is_staff
