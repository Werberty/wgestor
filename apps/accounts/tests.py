import pytest
from http import HTTPStatus
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core import mail
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.accounts.choices import RoleChoice
from apps.accounts.conftest import PASSWORD


pytestmark = pytest.mark.django_db


def test_password_reset_request_send_email(client, user):
    response = client.post(
        '/api/accounts/password-reset',
        data={'email': user.email}
    )
    
    assert response.status_code == HTTPStatus.OK
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


def test_password_reset_request_does_not_reveal_non_existent_emails(client):
    response = client.post(
        '/api/accounts/password-reset',
        data={'email': 'non.existent@email.com'}
    )

    assert response.status_code == HTTPStatus.OK
    assert len(mail.outbox) == 0


def test_password_reset_confirm_changes_successfuly(client, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    new_password = '12345678'
    response = client.post(
        '/api/accounts/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.check_password(new_password)


@pytest.mark.parametrize("token", ["token_invalido", "", "abc123789"])
def test_password_reset_confirm_invalid_token(client, user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    new_password = '12345678'
    response = client.post(
        '/api/accounts/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )
    
    assert response.status_code == HTTPStatus.BAD_REQUEST


def test_password_reset_confirm_invalid_link(client):
    uid = 'uid_invalid'
    token = 'token_invalid'

    new_password = '12345678'
    response = client.post(
        '/api/accounts/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )
    
    assert response.status_code == HTTPStatus.BAD_REQUEST


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
