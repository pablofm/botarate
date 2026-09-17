import re

from django.contrib.auth.decorators import login_not_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, Func, Q, Value
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import NotaForm, SocioForm
from .models import Nota, Socio


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

    def get_queryset(self):
        return super().get_queryset().prefetch_related('notas__autor')

    def get_success_url(self):
        return reverse('socios')


class NotaCreateView(SuccessMessageMixin, CreateView):
    """Apunta en la bitácora de una socia una interacción con ella."""

    model = Nota
    form_class = NotaForm
    template_name = 'socios/nota_form.html'

    @cached_property
    def socio(self):
        return get_object_or_404(Socio, pk=self.kwargs['pk'])

    def form_valid(self, form):
        form.instance.socio = self.socio
        form.instance.autor = self.request.user
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        return f'Nota añadida a la ficha de {self.socio.nombre}.'

    def get_success_url(self):
        # Se vuelve a la ficha, donde se ve la nota recién añadida en la bitácora.
        return reverse('socio_editar', args=[self.socio.pk])


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
