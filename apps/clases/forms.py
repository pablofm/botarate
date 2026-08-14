from django import forms

from .models import Alumno, Clase, Curso, DíaSemana, Socio


class CursoForm(forms.ModelForm):
    días_semana = forms.TypedMultipleChoiceField(
        label='Días de la semana',
        help_text='Días en los que se imparte el curso',
        choices=DíaSemana,
        coerce=int,
        widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Curso
        fields = '__all__'

    def clean_días_semana(self):
        return sorted(set(self.cleaned_data['días_semana']))

    def clean(self):
        cleaned_data = super().clean()
        principal = cleaned_data.get('profesor_principal')
        sustitutos = cleaned_data.get('profesores_sustitutos')
        if principal and sustitutos and principal in sustitutos:
            raise forms.ValidationError(
                f'{principal} ya es el profesor principal: los sustitutos han de ser otros.')
        return cleaned_data


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


class MatricularAlumnaForm(forms.Form):
    """Da de alta como alumna a alguien que ya es socia: no se piden datos otra vez."""

    socio = SocioChoiceField(
        label='Socia',
        queryset=Socio.objects.all(),
        empty_label='Elige una socia',
        help_text='Si no aparece, hay que darla de alta antes como socia.')
    curso = forms.ModelChoiceField(label='Curso', queryset=Curso.objects.none(), empty_label=None)

    def __init__(self, *args, cursos, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['curso'].queryset = cursos

    def clean(self):
        cleaned_data = super().clean()
        socio = cleaned_data.get('socio')
        curso = cleaned_data.get('curso')
        if socio and curso and Alumno.objects.filter(socio=socio, cursos=curso).exists():
            raise forms.ValidationError(f'{socio} ya está matriculada en {curso.nombre}.')
        return cleaned_data

    def matricular(self):
        alumno, _ = Alumno.objects.get_or_create(socio=self.cleaned_data['socio'])
        alumno.cursos.add(self.cleaned_data['curso'])
        return alumno


class TerminarClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = ['asistentes']
        labels = {'asistentes': 'Alumnas que han asistido'}
        widgets = {'asistentes': forms.CheckboxSelectMultiple}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asistentes'].queryset = self.instance.curso.alumnos.all()


class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get('curso')
        asistentes = cleaned_data.get('asistentes')
        if curso and asistentes:
            matriculados = set(curso.alumnos.values_list('pk', flat=True))
            ajenos = [str(alumno) for alumno in asistentes if alumno.pk not in matriculados]
            if ajenos:
                raise forms.ValidationError(
                    f"Estos alumnos no están matriculados en {curso.nombre}: {', '.join(ajenos)}")
        return cleaned_data