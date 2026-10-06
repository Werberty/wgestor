import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from .choices import RoleChoice


pytestmark = pytest.mark.django_db

PASSWORD = "Senha-segura-123!"


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        username="vendedor",
        password=PASSWORD,
        email="vendedor@example.com",
        name="Vendedor de teste",
        role=RoleChoice.SELLER,
    )


def test_login_returns_token_and_user_data(client, user):
    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "token": Token.objects.get(user=user).key,
        "user": {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
        },
    }

    client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    protected_response = client.get(reverse("accounts:me"))
    assert protected_response.status_code == status.HTTP_200_OK
    assert protected_response.data["id"] == user.pk


def test_login_reuses_existing_token(client, user):
    token = Token.objects.create(user=user)

    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["token"] == token.key
    assert Token.objects.filter(user=user).count() == 1


@pytest.mark.parametrize(
    "username,password",
    [("vendedor", "senha-incorreta"), ("inexistente", PASSWORD)],
)
def test_login_rejects_invalid_credentials(client, user, username, password):
    response = client.post(
        reverse("accounts:login"),
        {"username": username, "password": password},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "non_field_errors" in response.data
    assert "token" not in response.data
    assert not Token.objects.exists()


def test_login_rejects_inactive_user(client, user):
    user.is_active = False
    user.save(update_fields=["is_active"])

    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "non_field_errors" in response.data
    assert not Token.objects.exists()


@pytest.mark.parametrize(
    "payload,fields",
    [
        ({}, {"username", "password"}),
        ({"username": "vendedor"}, {"password"}),
        ({"password": PASSWORD}, {"username"}),
        ({"username": "", "password": PASSWORD}, {"username"}),
        ({"username": "vendedor", "password": ""}, {"password"}),
    ],
)
def test_login_requires_nonempty_credentials(client, payload, fields):
    response = client.post(reverse("accounts:login"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(response.data) == fields
    assert not Token.objects.exists()


def test_logout_revokes_token_and_blocks_further_access(client, user):
    token = Token.objects.create(user=user)
    token_key = token.key
    client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert response.content == b""
    assert not Token.objects.filter(key=token_key).exists()
    assert client.get(reverse("accounts:me")).status_code == status.HTTP_401_UNAUTHORIZED
    assert client.post(reverse("accounts:logout")).status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.parametrize("authorization", [None, "Token invalid-token", "Bearer invalid-token"])
def test_logout_rejects_missing_or_invalid_token(client, user, authorization):
    token = Token.objects.create(user=user)
    if authorization is not None:
        client.credentials(HTTP_AUTHORIZATION=authorization)

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert Token.objects.filter(key=token.key).exists()


def test_logout_preserves_other_users_tokens(client, user, django_user_model):
    other_user = django_user_model.objects.create_user(
        username="outro-vendedor",
        password=PASSWORD,
        name="Outro vendedor",
        role=RoleChoice.SELLER,
    )
    other_token = Token.objects.create(user=other_user)
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.post(reverse("accounts:logout"))

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Token.objects.filter(user=user).exists()
    assert Token.objects.filter(key=other_token.key, user=other_user).exists()


def test_login_after_logout_issues_new_token(client, user):
    old_token = Token.objects.create(user=user)
    old_key = old_token.key
    client.credentials(HTTP_AUTHORIZATION=f"Token {old_key}")
    assert client.post(reverse("accounts:logout")).status_code == status.HTTP_204_NO_CONTENT
    client.credentials()

    response = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["token"] != old_key
    assert Token.objects.get(user=user).key == response.data["token"]


@pytest.mark.parametrize("endpoint", ["accounts:login", "accounts:logout"])
def test_auth_endpoints_reject_get(client, user, endpoint):
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.get(reverse(endpoint))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    assert Token.objects.filter(key=token.key).exists()
