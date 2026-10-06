import pytest
from rest_framework.test import APIClient

from apps.accounts.factories import UserFactory


PASSWORD = "Senha-segura-123!"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory(password=PASSWORD)


@pytest.fixture(autouse=True)
def email_backend_setup(settings):
    settings.MAILERS['default']['BACKEND'] = "django.core.mail.backends.locmem.EmailBackend"
