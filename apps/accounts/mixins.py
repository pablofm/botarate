from django.contrib.auth.mixins import UserPassesTestMixin

from .roles import es_administración


class SoloAdministraciónMixin(UserPassesTestMixin):
    """Restringe la vista a la administración (staff o superusuarios), no al profesorado."""

    raise_exception = True

    def test_func(self):
        return es_administración(self.request.user)
