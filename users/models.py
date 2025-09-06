import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core import validators
from django.utils.translation import gettext_lazy as _
from autoslug import AutoSlugField
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from .managers import UserManager


class UsernameValidator(validators.RegexValidator):
    regex = r'^[a-zA-Z0-9_\.]+$'
    message = _(
        'Enter a valid username. This value may contain only letters, '
        'numbers, and @/./+/-/_ characters.'
    )
    flags = 0


class User(AbstractUser):
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    first_name = models.CharField(verbose_name=_('First Name'), max_length=150)
    last_name = models.CharField(verbose_name=_('Last Name'), max_length=150)
    email = models.EmailField(verbose_name=_('Email Address'), unique=True, db_index=True)
    username = models.CharField(
        verbose_name=_('Username'),
        max_length=150,
        validators=[UsernameValidator()],
    )

    # ----------------------------
    # Additional fields
    # ----------------------------
    avatar = models.ImageField(
        verbose_name=_("Avatar"),
        upload_to="avatars/",
        null=True,
        blank=True,
    )

    class Gender(models.TextChoices):
        MALE = "Male", _("Male")
        FEMALE = "Female", _("Female")
        OTHER = "Other", _("Other")

    gender = models.CharField(
        verbose_name=_("Gender"),
        max_length=10,
        choices=Gender.choices,
        default=Gender.OTHER,
    )

    class Occupation(models.TextChoices):
        NETWORK_ENGINEER = "network_engineer", _("Network Engineer")
        SYSTEM_ADMIN = "system_admin", _("System Administrator")
        DEVOPS_ENGINEER = "devops_engineer", _("DevOps Engineer")
        SECURITY_ANALYST = "security_analyst", _("Security Analyst")
        IT_MANAGER = "it_manager", _("IT Manager")
        TECH_SUPPORT = "tech_support", _("Technical Support")
        OTHER = "other", _("Other")

    occupation = models.CharField(
        verbose_name=_("Occupation"),
        choices=Occupation.choices,
        default=Occupation.OTHER,
    )

    bio = models.TextField(verbose_name=_("Bio"), null=True, blank=True)
    phone_number = PhoneNumberField(verbose_name=_("Phone Number"), null=True, blank=True)
    country = CountryField(verbose_name=_("Country"), null=True, blank=True, default="US")
    city_of_origin = models.CharField(
        verbose_name=_("City"),
        max_length=150,
        null=True,
        blank=True,
        default="New York",
    )

    slug = AutoSlugField(populate_from="username", unique=True)

    # ----------------------------
    # Email & Authentication settings
    # ----------------------------
    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-date_joined']

    def __str__(self) -> str:
        return self.username
