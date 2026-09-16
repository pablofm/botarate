from .roles import es_administración as _es_administración


def administración(request):
    """La cabecera necesita saber el rol en cualquier página, no solo en las que lo calculan."""
    return {'es_administración': _es_administración(request.user)}
