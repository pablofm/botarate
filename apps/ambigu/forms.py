from django import forms

from apps.pagos.forms import FormaPagoSelect

from .models import Bebida, CategoríaBebida, StockBebida, VentaBebida


class BebidaSelect(forms.Select):
    """Cada opción lleva el PVP de la bebida, para calcular el importe en el navegador."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            option['attrs']['data-precio'] = str(value.instance.precio_venta)
        return option


class BebidaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, bebida):
        return f'{bebida.nombre} ({bebida.categoría}) — {bebida.precio_venta} €'


def elegir_bebida(widget=forms.Select):
    return BebidaChoiceField(
        label='Bebida', queryset=Bebida.objects.select_related('categoría'), empty_label='Elige una bebida',
        widget=widget)


class CategoríaBebidaForm(forms.ModelForm):
    class Meta:
        model = CategoríaBebida
        fields = ['nombre']


class BebidaForm(forms.ModelForm):
    class Meta:
        model = Bebida
        fields = ['categoría', 'nombre', 'precio_venta', 'stock_mínimo']
        labels = {'categoría': 'Categoría', 'stock_mínimo': 'Stock mínimo'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['categoría'].empty_label = 'Elige una categoría'


class StockBebidaForm(forms.ModelForm):
    bebida = elegir_bebida()

    class Meta:
        model = StockBebida
        fields = ['bebida', 'fecha', 'cantidad', 'precio_compra']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class VentaBebidaForm(forms.ModelForm):
    bebida = elegir_bebida(widget=BebidaSelect)

    class Meta:
        model = VentaBebida
        fields = ['fecha', 'bebida', 'cantidad', 'forma_pago']
        widgets = {
            'forma_pago': FormaPagoSelect,
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # En el modelo puede quedar en blanco por las ventas antiguas, que no la
        # apuntaban; las nuevas sí tienen que decir cómo se han pagado.
        forma_pago = self.fields['forma_pago']
        forma_pago.required = self.instance._state.adding
        # Las opciones van como botones de radio: el guion de «sin elegir» sobra.
        forma_pago.choices = forma_pago.choices[1:]
