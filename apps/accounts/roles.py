def es_administración(usuario):
    """Administración (staff o superusuarios), por oposición al profesorado."""
    return usuario.is_staff or usuario.is_superuser
