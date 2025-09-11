from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from import_export.admin import ImportExportModelAdmin

from .forms import UserChangeForm, UserCreationForm
from .resources import UserResource

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin, ImportExportModelAdmin):
    resource_class = UserResource
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = ('pkid', 'id','email', 'username', 'first_name', 'last_name', 'is_active', 'is_staff')
    list_display_links = ('pkid', 'id', 'email', 'username')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'gender', 'occupation', 'country')
    ordering = ['pkid']
    readonly_fields = ['password', 'last_login', 'date_joined']
    fieldsets = (
        (_('Login Credentials'), {'fields': ('email', 'password')}),
        (_('User Info'), {'fields': ('username', 'first_name', 'last_name')}),
        (_('Personal Info'), {'fields': ('gender', 'occupation', 'bio', 'phone_number', 'country', 'city_of_origin', 'avatar')}),
        (_('Permissions and Groups'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
