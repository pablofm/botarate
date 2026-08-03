from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from .models import BotarateUser


class BotarateUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = BotarateUser
        fields = ('nombre', 'email',)


class BotarateUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = BotarateUser
        fields = '__all__'


class ActivarForm(forms.Form):
    email = forms.EmailField(
        label="Dirección de correo electrónico",
        widget=forms.TextInput(attrs={'placeholder': 'Dirección de correo electrónico'}))
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'placeholder': ''}),
        validators=[validate_password])
    password2 = forms.CharField(
        label="Repetir contraseña",
        widget=forms.PasswordInput(attrs={'placeholder': ''}),
        validators=[validate_password])

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("password2")
        if p1 != p2:
            raise forms.ValidationError('Las contraseñas no coinciden')
        try:
            user = get_user_model().objects.get(email=cleaned_data['email'])
        except get_user_model().DoesNotExist:
            raise forms.ValidationError('Indica un correo válido')

        if user.is_active:
            raise forms.ValidationError('Indica un correo válido')

        return cleaned_data
