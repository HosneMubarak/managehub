from django import forms
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm as BaseUserCreationForm
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import SignupForm
from django_countries.widgets import CountrySelectWidget

User = get_user_model()

class UserChangeForm(BaseUserCreationForm):
    class Meta(BaseUserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')

class UserCreationForm(admin_forms.UserCreationForm):
    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = ('email', 'username', 'first_name', 'last_name')

    error_message = {
        'duplicate_username': 'A user with that username already exists.',
        'duplicate_email': 'A user with that email already exists.',
    }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                self.error_messages["duplicate_email"]
            )
        return email
    def clean_username(self) -> str:
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(
                self.error_messages["duplicate_username"]
            )
        return username

class CustomSignupForm(SignupForm):
    """Custom signup form that includes first_name, last_name, and optional username"""

    first_name = forms.CharField(
        max_length=150,
        label=_('First Name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('First name')
        })
    )

    last_name = forms.CharField(
        max_length=150,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Last name')
        })
    )

    username = forms.CharField(
        max_length=150,
        label=_('Username'),
        required=False,  # Make username optional
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Username (optional)')
        }),
        help_text=_('Leave blank to auto-generate from email')
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to existing fields
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your email')
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control create-password-input',
            'placeholder': _('Enter password')
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control create-password-input',
            'placeholder': _('Confirm password')
        })

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Only set username if provided, otherwise let UserManager auto-generate
        username = self.cleaned_data.get('username')
        if username:
            user.username = username
        
        user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """Form for updating user profile information"""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'avatar',
            'bio', 'phone_number', 'country', 'city_of_origin',
            'gender', 'occupation'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('First name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Last name')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Email address')
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'occupation': forms.Select(attrs={
                'class': 'form-select'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Tell us about yourself...')
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Phone number')
            }),
            'country': CountrySelectWidget(attrs={
                'class': 'form-select'
            }),
            'city_of_origin': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('City')
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email field required
        self.fields['email'].required = True
        # Add help text for some fields
        self.fields['avatar'].help_text = _('Upload a profile picture (optional)')
