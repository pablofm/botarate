from django.contrib.auth.mixins import UserPassesTestMixin


def es_administración(usuario):
    return usuario.is_staff or usuario.is_superuser


class SoloAdministraciónMixin(UserPassesTestMixin):
    """Restringe la vista a la administración (staff o superusuarios), no al profesorado."""

    raise_exception = True

    def test_func(self):
        return es_administración(self.request.user)
