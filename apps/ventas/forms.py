from django import forms

from apps.pagos.forms import FormaPagoSelect

from .models import Bebida, Camiseta, CategoríaBebida, StockBebida, StockCamiseta, VentaBebida, VentaCamiseta


class PrecioSelect(forms.Select):
    """Cada opción lleva el PVP del producto, para calcular el importe en el navegador."""

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


class FormaPagoEnBotonesMixin:
    """La forma de pago va como botones de radio, sin la opción de «sin elegir»."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        forma_pago = self.fields['forma_pago']
        forma_pago.choices = [opción for opción in forma_pago.choices if opción[0]]


class VentaBebidaForm(FormaPagoEnBotonesMixin, forms.ModelForm):
    bebida = elegir_bebida(widget=PrecioSelect)

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
        self.fields['forma_pago'].required = self.instance._state.adding


class CamisetaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, camiseta):
        return f'{camiseta} — {camiseta.precio_venta} €'


def elegir_camiseta(widget=forms.Select):
    return CamisetaChoiceField(
        label='Camiseta', queryset=Camiseta.objects.all(), empty_label='Elige una camiseta', widget=widget)


class StockCamisetaForm(forms.ModelForm):
    camiseta = elegir_camiseta()

    class Meta:
        model = StockCamiseta
        fields = ['camiseta', 'fecha', 'cantidad']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }


class VentaCamisetaForm(FormaPagoEnBotonesMixin, forms.ModelForm):
    camiseta = elegir_camiseta(widget=PrecioSelect)

    class Meta:
        model = VentaCamiseta
        fields = ['fecha', 'camiseta', 'cantidad', 'forma_pago']
        widgets = {
            'forma_pago': FormaPagoSelect,
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }
