from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db import models

from apps.accounts.choices import RoleChoice
from apps.core.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    name = models.CharField(verbose_name=_('Nome'), max_length=150)
    role = models.CharField(
        verbose_name=_('Função'), max_length=50, choices=RoleChoice.choices
    )