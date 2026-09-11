from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from apps.accounts.mixins import SoloAdministraciónMixin
from apps.clases.models import Alumno

from .forms import PagoForm
from .models import Pago


class PagoListView(SoloAdministraciónMixin, ListView):
    model = Pago
    template_name = 'pagos/pago_list.html'
    context_object_name = 'pagos'

    def get_queryset(self):
        return super().get_queryset().select_related('alumno__socio', 'curso', 'registrado_por')


class PagoCreateView(SoloAdministraciónMixin, CreateView):
    model = Pago
    form_class = PagoForm
    template_name = 'pagos/pago_form.html'
    success_url = reverse_lazy('pagos')

    def get_initial(self):
        initial = super().get_initial()
        # Desde la ficha del curso llega ya elegida la alumna a la que se cobra.
        alumno, curso = self.request.GET.get('alumno'), self.request.GET.get('curso')
        if alumno and curso:
            matrícula = Alumno.cursos.through.objects.filter(alumno=alumno, curso=curso).first()
            if matrícula:
                initial['matrícula'] = matrícula
        return initial

    def form_valid(self, form):
        form.instance.registrado_por = self.request.user
        respuesta = super().form_valid(form)
        pago = self.object
        messages.success(
            self.request,
            f'Pago de {pago.importe} € de {pago.alumno} para {pago.curso.nombre} registrado.')
        return respuesta
