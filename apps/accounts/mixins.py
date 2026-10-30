from django.contrib.auth.mixins import UserPassesTestMixin

from .roles import es_administración, es_staff


class SoloAdministraciónMixin(UserPassesTestMixin):
    """Restringe la vista a la administración (staff o superusuarios), no al profesorado."""

    raise_exception = True

    def test_func(self):
        return es_administración(self.request.user)


class SoloStaffMixin(UserPassesTestMixin):
    """Restringe la vista al staff: ni el profesorado ni un superusuario que no sea staff."""

    raise_exception = True

    def test_func(self):
        return es_staff(self.request.user)
