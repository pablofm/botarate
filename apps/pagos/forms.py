from django import forms

from apps.clases.models import Alumno

from .models import FORMAS_PAGO_PENDIENTES, Pago


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
        queryset=Alumno.cursos.through.objects
        .select_related('alumno__socio', 'curso')
        .order_by('alumno__socio__nombre', 'curso__nombre'),
        empty_label='Elige una alumna',
        help_text='Solo aparecen las alumnas matriculadas, una vez por cada curso.')

    class Meta:
        model = Pago
        fields = ['modalidad', 'desde', 'importe', 'forma_pago', 'fecha']
        widgets = {
            'modalidad': forms.RadioSelect,
            'forma_pago': FormaPagoSelect,
            'desde': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    field_order = ['matrícula', 'modalidad', 'desde', 'importe', 'forma_pago', 'fecha']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Las opciones van como botones de radio: el guion de «sin elegir» sobra.
        for campo in ('modalidad', 'forma_pago'):
            self.fields[campo].choices = self.fields[campo].choices[1:]

    def clean(self):
        cleaned_data = super().clean()
        matrícula = cleaned_data.get('matrícula')
        if matrícula:
            # Antes de que ModelForm valide el modelo, que ya necesita saber a quién se cobra.
            self.instance.alumno = matrícula.alumno
            self.instance.curso = matrícula.curso
        return cleaned_data
