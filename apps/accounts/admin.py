from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import BotarateUserChangeForm, BotarateUserCreationForm
from .models import BotarateUser


@admin.register(BotarateUser)
class BotarateUserAdmin(UserAdmin):
    add_form = BotarateUserCreationForm
    form = BotarateUserChangeForm
    model = BotarateUser
    list_display = ('nombre', 'email', 'is_staff', 'is_active', 'is_superuser',)
    list_filter = ('is_staff', 'is_active', 'is_superuser',)
    fieldsets = (
        ('Datos básicos', {'fields': ('nombre', 'email', 'password')}),
        ('Control de acceso', {'fields': ('is_staff', 'is_active', 'is_superuser')}),
        ('Grupos', {'fields': ('groups', )}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('nombre', 'email', 'password1', 'password2')
        }),
        ('Control de acceso', {
            'classes': ('wide',),
            'fields': ('is_staff', 'is_active', 'is_superuser')
        }),
    )
    filter_horizontal = ('groups',)
    search_fields = ('nombre', 'email',)
    ordering = ('email',)