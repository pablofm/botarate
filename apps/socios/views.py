import re
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_not_required
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count, F, Func, Min, Q, Value
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from apps.clases.models import Matrícula

from .forms import NotaForm, SocioForm
from .models import Nota, Socio


class SocioListView(ListView):
    model = Socio
    template_name = 'socios/socio_list.html'
    context_object_name = 'socios'

    # Los separadores que admite validar_teléfono: se ignoran al buscar.
    SEPARADORES_TELÉFONO = r'[\s.-]'

    # Las columnas por las que se puede ordenar, con el sentido en que se ordenan al
    # pulsarlas la primera vez: la fecha, de la más reciente; las notas, de más a menos.
    COLUMNAS_ORDENABLES = {'fecha_alta': '-', 'nombre': '', 'cursos': '', 'notas': '-'}
    ORDEN_POR_DEFECTO = 'nombre'

    @cached_property
    def búsqueda(self):
        return self.request.GET.get('q', '').strip()

    @cached_property
    def orden(self):
        orden = self.request.GET.get('orden', '')
        return orden if orden.lstrip('-') in self.COLUMNAS_ORDENABLES else self.ORDEN_POR_DEFECTO

    def get_queryset(self):
        socios = super().get_queryset().prefetch_related('alumno__cursos', 'notas__autor')
        return self.ordenar(self.buscar(socios))

    def ordenar(self, socios):
        columna = self.orden.lstrip('-')
        # Por cursos se agrupan según el primero en orden alfabético.
        if columna == 'cursos':
            socios = socios.annotate(primer_curso=Min('alumno__cursos__nombre'))
            columna = 'primer_curso'
        elif columna == 'notas':
            socios = socios.annotate(número_notas=Count('notas'))
            columna = 'número_notas'
        # Quien no va a clase queda al final en los dos sentidos.
        if self.orden.startswith('-'):
            criterio = F(columna).desc(nulls_last=True)
        else:
            criterio = F(columna).asc(nulls_last=True)
        return socios.order_by(criterio, 'nombre', 'pk')

    def buscar(self, socios):
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

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['columnas'] = {columna: self.enlace_para_ordenar(columna)
                                for columna in self.COLUMNAS_ORDENABLES}
        return contexto

    def enlace_para_ordenar(self, columna):
        """El sentido en que está ordenada la columna y el enlace que la ordena al pulsarla."""
        if self.orden.lstrip('-') == columna:
            descendente = self.orden.startswith('-')
            sentido = 'descending' if descendente else 'ascending'
            # Pulsar la columna por la que ya se ordena le da la vuelta.
            orden = columna if descendente else f'-{columna}'
        else:
            sentido = None
            orden = self.COLUMNAS_ORDENABLES[columna] + columna
        parámetros = {'q': self.búsqueda} if self.búsqueda else {}
        parámetros['orden'] = orden
        return {'sentido': sentido, 'url': f'?{urlencode(parámetros)}'}


class SocioUpdateView(SuccessMessageMixin, UpdateView):
    """Corrige la ficha de una socia ya dada de alta, desde el listado."""

    model = Socio
    form_class = SocioForm
    template_name = 'socios/socio_editar.html'
    success_message = 'Ficha de %(nombre)s actualizada.'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('notas__autor')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['matrículas'] = Matrícula.objects.filter(alumno__socio=self.object).select_related('curso').order_by(
            'curso__días_semana', 'curso__hora_inicio', 'curso__nombre')
        return context

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
