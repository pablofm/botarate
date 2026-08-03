from django import forms

from .models import Clase, Curso, DíaSemana


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
            ajenos = [alumno.nombre for alumno in asistentes if alumno.curso_id != curso.pk]
            if ajenos:
                raise forms.ValidationError(
                    f"Estos alumnos no están matriculados en {curso.nombre}: {', '.join(ajenos)}")
        return cleaned_data