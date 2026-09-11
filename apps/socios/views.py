import re

from django.contrib.auth.decorators import login_not_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Func, Q, Value
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import SocioForm
from .models import Socio


class SocioListView(ListView):
    model = Socio
    template_name = 'socios/socio_list.html'
    context_object_name = 'socios'

    # Los separadores que admite validar_teléfono: se ignoran al buscar.
    SEPARADORES_TELÉFONO = r'[\s.-]'

    @cached_property
    def búsqueda(self):
        return self.request.GET.get('q', '').strip()

    def get_queryset(self):
        socios = super().get_queryset().prefetch_related('alumno__cursos')
        if not self.búsqueda:
            return socios

        # unaccent se aplica a los dos lados: «Garcia» encuentra «García» y al revés.
        coincide = (Q(nombre__unaccent__icontains=self.búsqueda)
                    | Q(documento__icontains=self.búsqueda)
                    | Q(email__unaccent__icontains=self.búsqueda))
        # Sin separadores, «600123» encuentra «600 123 456»; si la búsqueda era solo
        # separadores no queda nada que buscar, y con '' coincidirían todas.
        if teléfono := re.sub(self.SEPARADORES_TELÉFONO, '', self.búsqueda):
            socios = socios.annotate(teléfono_sin_separadores=Func(
                F('teléfono'), Value(self.SEPARADORES_TELÉFONO), Value(''), Value('g'),
                function='REGEXP_REPLACE'))
            coincide |= Q(teléfono_sin_separadores__contains=teléfono)
        return socios.filter(coincide)


class SocioUpdateView(SuccessMessageMixin, UpdateView):
    """Corrige la ficha de una socia ya dada de alta, desde el listado."""

    model = Socio
    form_class = SocioForm
    template_name = 'socios/socio_editar.html'
    success_message = 'Ficha de %(nombre)s actualizada.'

    def get_success_url(self):
        return reverse('socios')


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
