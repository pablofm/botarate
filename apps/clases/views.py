from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.functional import cached_property
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import TerminarClaseForm
from .models import Alumno, Clase, Curso


class DashboardView(ListView):
    model = Curso
    template_name = 'dashboard.html'
    context_object_name = 'cursos'

    def get_queryset(self):
        # El annotate() introduce un GROUP BY y Django descarta ahí el Meta.ordering
        # del modelo, así que hay que repetirlo a mano.
        return (super().get_queryset()
                .select_related('profesor_principal')
                .annotate(total_alumnos=Count('alumnos'))
                .order_by(*Curso._meta.ordering))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        usuario = self.request.user
        gestionables = set(Curso.objects.gestionables_por(usuario).values_list('pk', flat=True))
        # Solo puede haber una clase abierta por profesor, así que basta con buscarla una vez.
        abierta = Clase.objects.filter(profesor=usuario, fin__isnull=True).first()

        cursos = list(context['cursos'])
        for curso in cursos:
            curso.clase_abierta = abierta if abierta and abierta.curso_id == curso.pk else None
            curso.puede_iniciar_clase = abierta is None and curso.pk in gestionables

        context['cursos'] = cursos
        context['puede_añadir_alumnos'] = bool(gestionables)
        return context


class CursoDetailView(DetailView):
    model = Curso
    template_name = 'clases/curso_detail.html'
    context_object_name = 'curso'

    def get_queryset(self):
        clases = Clase.objects.select_related('profesor').prefetch_related('asistentes')
        return (super().get_queryset()
                .select_related('profesor_principal')
                .prefetch_related('alumnos', Prefetch('clases', queryset=clases)))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['puede_añadir_alumnos'] = self.object.gestionable_por(self.request.user)
        return context


class AlumnoCreateView(UserPassesTestMixin, SuccessMessageMixin, CreateView):
    model = Alumno
    fields = ['nombre', 'curso']
    template_name = 'clases/alumno_form.html'
    success_message = '%(nombre)s se ha dado de alta en %(curso)s.'
    raise_exception = True

    @cached_property
    def cursos_gestionables(self):
        return Curso.objects.gestionables_por(self.request.user)

    def test_func(self):
        return self.cursos_gestionables.exists()

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['curso'].queryset = self.cursos_gestionables
        return form

    def get_initial(self):
        initial = super().get_initial()
        curso = self.request.GET.get('curso')
        if curso:
            initial['curso'] = curso
        return initial

    def get_success_url(self):
        return reverse('curso_detalle', args=[self.object.curso_id])


class IniciarClaseView(View):
    """Abre una clase del curso indicado, a nombre de quien pulsa el botón."""

    def post(self, request, pk):
        curso = get_object_or_404(Curso, pk=pk)
        if not curso.gestionable_por(request.user):
            raise PermissionDenied

        abierta = Clase.objects.filter(profesor=request.user, fin__isnull=True).first()
        if abierta:
            messages.warning(
                request,
                f'Ya tienes una clase de {abierta.curso.nombre} sin terminar.')
            return redirect('clase_terminar', pk=abierta.pk)

        clase = Clase.objects.create(curso=curso, profesor=request.user, inicio=timezone.now())
        messages.success(request, f'Clase de {curso.nombre} iniciada a las {timezone.localtime(clase.inicio):%H:%M}.')
        return redirect('dashboard')


class TerminarClaseView(SuccessMessageMixin, UpdateView):
    """Cierra la clase abierta: anota las asistentes y la hora de fin."""

    model = Clase
    form_class = TerminarClaseForm
    template_name = 'clases/clase_terminar.html'
    success_url = reverse_lazy('dashboard')
    success_message = 'Clase de %(curso)s terminada.'

    def get_queryset(self):
        # Solo el profesor que la abrió puede cerrarla, y solo mientras siga abierta.
        return (super().get_queryset()
                .filter(profesor=self.request.user, fin__isnull=True)
                .select_related('curso'))

    def form_valid(self, form):
        form.instance.fin = timezone.now()
        return super().form_valid(form)

    def get_success_message(self, cleaned_data):
        asistentes = len(cleaned_data['asistentes'])
        return (f'Clase de {self.object.curso.nombre} terminada '
                f'a las {timezone.localtime(self.object.fin):%H:%M}, con {asistentes} asistentes.')
