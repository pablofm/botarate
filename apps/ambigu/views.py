from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import F, ProtectedError
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from apps.accounts.mixins import SoloAdministraciónMixin

from .forms import BebidaForm, CategoríaBebidaForm, StockBebidaForm, VentaBebidaForm
from .models import Bebida, CategoríaBebida, StockBebida, VentaBebida


class AmbigúMixin(SoloAdministraciónMixin):
    """Todas las páginas del ambigú avisan de las bebidas que hay que comprar."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Si están justo en el stock mínimo aún no hace falta comprar.
        context['por_reponer'] = Bebida.objects.con_stock().filter(stock_actual__lt=F('stock_mínimo'))
        return context


class FormularioMixin(AmbigúMixin, SuccessMessageMixin):
    """Alta y edición comparten plantilla: cambian el título y el botón."""

    template_name = 'ambigu/form.html'
    # Lo que se da de alta o se edita, con artículo: «una bebida».
    nombre = ''
    sección = ''

    def get_success_url(self):
        return reverse_lazy(self.sección)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.object:
            context['título'] = f'Editar {self.object}'
            context['botón'] = 'Guardar cambios'
        else:
            context['título'] = f'Registrar {self.nombre}'
            context['botón'] = 'Registrar'
        context['sección'] = self.sección
        return context


class RegistradoPorMixin:
    """Quien da de alta el registro queda apuntado; al editarlo no cambia."""

    def form_valid(self, form):
        if not form.instance.pk:
            form.instance.registrado_por = self.request.user
        return super().form_valid(form)


class EliminarMixin(SoloAdministraciónMixin):
    # Se confirma en el diálogo del listado, así que no hay página propia que servir por GET.
    http_method_names = ['post']
    sección = ''
    en_uso = ''

    def get_success_url(self):
        return reverse_lazy(self.sección)

    def form_valid(self, form):
        descripción = str(self.object)
        try:
            respuesta = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, f'No se puede eliminar «{descripción}»: {self.en_uso}.')
            return redirect(self.sección)
        messages.success(self.request, f'Se ha eliminado «{descripción}».')
        return respuesta


class BebidaListView(AmbigúMixin, ListView):
    """La carta del ambigú."""

    model = Bebida
    template_name = 'ambigu/bebida_list.html'
    context_object_name = 'bebidas'

    def get_queryset(self):
        return super().get_queryset().select_related('categoría').con_stock()


class BebidaCreateView(FormularioMixin, CreateView):
    model = Bebida
    form_class = BebidaForm
    nombre = 'una bebida'
    sección = 'bebidas'
    success_message = 'Bebida %(nombre)s registrada.'


class BebidaUpdateView(FormularioMixin, UpdateView):
    model = Bebida
    form_class = BebidaForm
    sección = 'bebidas'
    success_message = 'Bebida %(nombre)s actualizada.'


class BebidaDeleteView(EliminarMixin, DeleteView):
    model = Bebida
    sección = 'bebidas'
    en_uso = 'tiene compras o ventas registradas'


class CategoríaBebidaListView(AmbigúMixin, ListView):
    model = CategoríaBebida
    template_name = 'ambigu/categoria_list.html'
    context_object_name = 'categorías'

    def get_queryset(self):
        return super().get_queryset().prefetch_related('bebidas')


class CategoríaBebidaCreateView(FormularioMixin, CreateView):
    model = CategoríaBebida
    form_class = CategoríaBebidaForm
    nombre = 'una categoría'
    sección = 'categorias_bebida'
    success_message = 'Categoría %(nombre)s registrada.'


class CategoríaBebidaUpdateView(FormularioMixin, UpdateView):
    model = CategoríaBebida
    form_class = CategoríaBebidaForm
    sección = 'categorias_bebida'
    success_message = 'Categoría %(nombre)s actualizada.'


class CategoríaBebidaDeleteView(EliminarMixin, DeleteView):
    model = CategoríaBebida
    sección = 'categorias_bebida'
    en_uso = 'todavía tiene bebidas'


class StockBebidaListView(AmbigúMixin, ListView):
    """Las compras de bebida, de la más reciente a la más antigua."""

    model = StockBebida
    template_name = 'ambigu/stock_list.html'
    context_object_name = 'entradas'

    def get_queryset(self):
        return super().get_queryset().select_related('bebida', 'registrado_por')


class StockBebidaCreateView(FormularioMixin, RegistradoPorMixin, CreateView):
    model = StockBebida
    form_class = StockBebidaForm
    nombre = 'una compra de bebida'
    sección = 'stock_bebidas'
    success_message = 'Compra de %(cantidad)s × %(bebida)s registrada.'


class StockBebidaUpdateView(FormularioMixin, UpdateView):
    model = StockBebida
    form_class = StockBebidaForm
    sección = 'stock_bebidas'
    success_message = 'Compra de %(cantidad)s × %(bebida)s actualizada.'


class StockBebidaDeleteView(EliminarMixin, DeleteView):
    model = StockBebida
    sección = 'stock_bebidas'


class VentaBebidaListView(AmbigúMixin, ListView):
    """Las ventas en barra, de la más reciente a la más antigua."""

    model = VentaBebida
    template_name = 'ambigu/venta_list.html'
    context_object_name = 'ventas'

    def get_queryset(self):
        return super().get_queryset().select_related('bebida', 'registrado_por')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total'] = sum(venta.importe for venta in context['ventas'])
        return context


class VentaBebidaCreateView(FormularioMixin, RegistradoPorMixin, CreateView):
    model = VentaBebida
    form_class = VentaBebidaForm
    template_name = 'ambigu/venta_form.html'
    nombre = 'una venta'
    sección = 'ventas_bebidas'
    success_message = 'Venta de %(cantidad)s × %(bebida)s registrada.'


class VentaBebidaUpdateView(FormularioMixin, UpdateView):
    model = VentaBebida
    form_class = VentaBebidaForm
    template_name = 'ambigu/venta_form.html'
    sección = 'ventas_bebidas'
    success_message = 'Venta de %(cantidad)s × %(bebida)s actualizada.'


class VentaBebidaDeleteView(EliminarMixin, DeleteView):
    model = VentaBebida
    sección = 'ventas_bebidas'
