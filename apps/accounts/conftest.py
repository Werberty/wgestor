import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import UserFactory


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory.create()


@pytest.fixture(autouse=True)
def email_backend_setup(settings):
    settings.MAILERS['default']['BACKEND'] = "django.core.mail.backends.locmem.EmailBackend"
