from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .forms import UserChangeForm, UserCreationForm

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('pkid', 'id','email', 'username', 'first_name', 'last_name', 'is_superuser')
    list_display_links = ('pkid', 'id', 'email', 'username')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ['pkid']
    readonly_fields = ['password', 'last_login', 'date_joined']
    fieldsets = (
        (_('Login Credentials'), {'fields': ('email', 'password')}),
        (_('User Info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions and Groups'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
