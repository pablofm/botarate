from django.contrib.auth.decorators import login_not_required
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, ListView, TemplateView

from .forms import SocioForm
from .models import Socio


class SocioListView(ListView):
    model = Socio
    template_name = 'socios/socio_list.html'
    context_object_name = 'socios'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('alumno__cursos')


@method_decorator(login_not_required, name='dispatch')
class SocioCreateView(SuccessMessageMixin, CreateView):
    """La portada: cualquiera puede hacerse socio, que es a donde apunta el QR."""

    model = Socio
    form_class = SocioForm
    template_name = 'socios/socio_form.html'
    success_message = '%(nombre)s se ha dado de alta como socia.'

    def get_success_url(self):
        # Quien llega por el QR no tiene acceso al resto de la aplicación.
        if self.request.user.is_authenticated:
            return reverse('socios')
        return reverse('alta_hecha')

    def get_success_message(self, cleaned_data):
        if not self.request.user.is_authenticated:
            return ''
        return super().get_success_message(cleaned_data)


@method_decorator(login_not_required, name='dispatch')
class AltaHechaView(TemplateView):
    template_name = 'socios/alta_hecha.html'
