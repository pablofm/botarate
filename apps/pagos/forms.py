from bootstrap_datepicker_plus.widgets import MonthPickerInput
from django import forms

from apps.clases.models import Matrícula

from .models import FORMAS_PAGO_PENDIENTES, Modalidad, Pago


class FormaPagoSelect(forms.RadioSelect):
    """Enseña también las formas de pago aún sin activar, pero sin dejar elegirlas."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value in FORMAS_PAGO_PENDIENTES:
            option['attrs']['disabled'] = True
            option['label'] = f'{label} (pendiente de activar)'
        return option


class MatrículaChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, matrícula):
        socio = matrícula.alumno.socio
        return f'{socio.nombre} ({socio.documento}) — {matrícula.curso.nombre}'


class PagoForm(forms.ModelForm):
    # Se elige la matrícula, y no alumna y curso por separado, para que no se pueda
    # cobrar a nadie un curso al que no va.
    matrícula = MatrículaChoiceField(
        label='Alumna y curso',
        queryset=Matrícula.objects
        .select_related('alumno__socio', 'curso')
        .order_by('alumno__socio__nombre', 'curso__nombre'),
        empty_label='Elige una alumna',
        help_text='Solo aparecen las alumnas matriculadas, una vez por cada curso.')
    # Se paga por meses naturales: basta con elegir el mes, y se guarda su día 1. La
    # clase suelta no lo necesita, porque cubre el día del pago.
    desde = forms.DateField(
        label='Desde',
        required=False,
        widget=MonthPickerInput,
        help_text='Mes en que empieza lo que cubre el pago.')

    class Meta:
        model = Pago
        fields = ['modalidad', 'desde', 'importe', 'forma_pago', 'fecha', 'recibo_enviado']
        widgets = {
            'modalidad': forms.RadioSelect,
            'forma_pago': FormaPagoSelect,
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    # En el mismo orden que la venta de bebidas: fecha, a quién, importe y forma de pago.
    field_order = ['fecha', 'matrícula', 'importe', 'forma_pago', 'modalidad', 'desde',
                   'recibo_enviado']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Las opciones van como botones de radio: el guion de «sin elegir» sobra.
        for campo in ('modalidad', 'forma_pago'):
            self.fields[campo].choices = self.fields[campo].choices[1:]
        if self.instance.pk:
            matrícula = Matrícula.objects.filter(
                alumno=self.instance.alumno_id, curso=self.instance.curso_id).first()
            if matrícula:
                self.initial['matrícula'] = matrícula
            else:
                # Se desmatriculó: el pago sigue siendo suyo, pero ya no se puede elegir en
                # la lista, así que no se deja cambiar a quién se cobró.
                del self.fields['matrícula']

    def clean(self):
        cleaned_data = super().clean()
        modalidad, desde = cleaned_data.get('modalidad'), cleaned_data.get('desde')
        if modalidad == Modalidad.CLASE:
            cleaned_data['desde'] = cleaned_data.get('fecha')
        elif modalidad and not desde:
            self.add_error('desde', 'Elige el mes en que empieza lo que cubre el pago.')
        elif desde:
            cleaned_data['desde'] = desde.replace(day=1)
        matrícula = cleaned_data.get('matrícula')
        if matrícula:
            # Antes de que ModelForm valide el modelo, que ya necesita saber a quién se cobra.
            self.instance.alumno = matrícula.alumno
            self.instance.curso = matrícula.curso
        return cleaned_data
