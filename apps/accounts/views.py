from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import get_default_password_validators
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView

from .forms import ActivarForm


class LoginView(LoginView):
    form_class = AuthenticationForm
    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context['activado'] = self.request.GET.get('activado', False)
        return context


@method_decorator(login_not_required, name='dispatch')
class ActivarView(FormView):
    form_class = ActivarForm
    template_name = 'accounts/activar.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = get_user_model().objects.get(email=form.cleaned_data['email'])
        user.set_password(form.cleaned_data['password'])
        user.is_active = True
        user.save()
        return super().form_valid(form)

    def get_success_url(self):
        return f"{reverse_lazy('login')}?activado=True"

    def get_context_data(self, **kwargs):
        context = super(ActivarView, self).get_context_data(**kwargs)
        validators = get_default_password_validators()
        requirements = [validator.get_help_text() for validator in validators]
        context['password_requirements'] = requirements
        context['activado'] = self.request.GET.get('activado', False)
        return context
