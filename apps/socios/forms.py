from django import forms

from .models import Socio


class SocioForm(forms.ModelForm):
    CONSENTIMIENTOS_OBLIGATORIOS = ('acepta_tratamiento_datos', 'acepta_inscripción')

    class Meta:
        model = Socio
        fields = ['nombre', 'dni', 'teléfono', 'email',
                  'acepta_tratamiento_datos', 'acepta_inscripción',
                  'quiere_comunicaciones', 'quiere_whatsapp']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Django genera los BooleanField del modelo siempre como opcionales, así que
        # los consentimientos legales hay que exigirlos aquí.
        for consentimiento in self.CONSENTIMIENTOS_OBLIGATORIOS:
            self.fields[consentimiento].required = True


class SocioChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, socio):
        return f'{socio.nombre} ({socio.dni})'
