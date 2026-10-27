import pytest
from http import HTTPStatus
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core import mail
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.accounts.choices import RoleChoice
from apps.accounts.conftest import PASSWORD
from apps.accounts.factories import UserFactory


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


NEW_PASSWORD = "Outra-senha-segura-456!"


@pytest.fixture
def password_change_token(client, user):
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return token


@pytest.mark.parametrize("prefix", ["/api/accounts", "/api/auth"])
def test_password_change_updates_password_and_revokes_access(
    client, user, password_change_token, prefix
):
    response = client.post(
        f"{prefix}/password-change/",
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data == {
        "detail": "Senha alterada com sucesso. Faça login novamente"
    }
    user.refresh_from_db()
    assert user.password != NEW_PASSWORD
    assert user.check_password(NEW_PASSWORD)
    assert not user.check_password(PASSWORD)
    assert not Token.objects.filter(user=user).exists()
    assert client.get(reverse("accounts:me")).status_code == status.HTTP_401_UNAUTHORIZED
    repeated_response = client.post(
        reverse("accounts:password-change"),
        {"current_password": NEW_PASSWORD, "new_password": PASSWORD},
        format="json",
    )
    assert repeated_response.status_code == status.HTTP_401_UNAUTHORIZED
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)


def test_password_change_allows_login_only_with_new_password(
    client, user, password_change_token
):
    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    client.credentials()

    old_login = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": PASSWORD},
        format="json",
    )
    assert old_login.status_code == status.HTTP_400_BAD_REQUEST
    assert not Token.objects.filter(user=user).exists()

    new_login = client.post(
        reverse("accounts:login"),
        {"username": user.username, "password": NEW_PASSWORD},
        format="json",
    )
    assert new_login.status_code == status.HTTP_200_OK
    assert new_login.data["token"] != password_change_token.key
    assert Token.objects.get(user=user).key == new_login.data["token"]
    client.credentials(HTTP_AUTHORIZATION=f"Token {new_login.data['token']}")
    assert client.get(reverse("accounts:me")).status_code == status.HTTP_200_OK


@pytest.mark.parametrize(
    "current_password,new_password,field,message",
    [
        ("senha-incorreta", NEW_PASSWORD, "current_password", "Senha atual incorreta."),
        (PASSWORD, PASSWORD, "new_password", "A nova senha deve ser diferente da atual."),
    ],
)
def test_password_change_rejects_incorrect_or_reused_password(
    client, user, password_change_token, current_password, new_password, field, message
):
    original_hash = user.password
    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": current_password, "new_password": new_password},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data == {field: [message]}
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()


@pytest.mark.parametrize(
    "new_password,error_code",
    [
        ("Ab!2x", "password_too_short"),
        ("password", "password_too_common"),
        ("928471603582", "password_entirely_numeric"),
        ("vendedor-exemplo", "password_too_similar"),
    ],
    ids=["too-short", "too-common", "numeric", "similar-to-user"],
)
def test_password_change_applies_configured_password_validators(
    client, user, password_change_token, new_password, error_code
):
    user.username = "vendedor-exemplo"
    user.save(update_fields=["username"])
    original_hash = user.password

    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": PASSWORD, "new_password": new_password},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(response.data) == {"new_password"}

    with pytest.raises(ValidationError) as exc_info:
        validate_password(new_password, user=user)
    assert error_code in [error.code for error in exc_info.value.error_list]
    assert response.data["new_password"] == exc_info.value.messages
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()


@pytest.mark.parametrize(
    "payload,fields",
    [
        ({}, {"current_password", "new_password"}),
        ({"current_password": PASSWORD}, {"new_password"}),
        ({"new_password": NEW_PASSWORD}, {"current_password"}),
        ({"current_password": "", "new_password": NEW_PASSWORD}, {"current_password"}),
        ({"current_password": PASSWORD, "new_password": ""}, {"new_password"}),
        ({"current_password": None, "new_password": NEW_PASSWORD}, {"current_password"}),
        ({"current_password": PASSWORD, "new_password": None}, {"new_password"}),
    ],
)
def test_password_change_requires_nonempty_passwords(
    client, user, password_change_token, payload, fields
):
    original_hash = user.password
    response = client.post(reverse("accounts:password-change"), payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert set(response.data) == fields
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()


@pytest.mark.parametrize("authorization", [None, "Token invalid-token", "Bearer invalid-token"])
def test_password_change_rejects_missing_or_invalid_token(client, user, authorization):
    token = Token.objects.create(user=user)
    original_hash = user.password
    if authorization is not None:
        client.credentials(HTTP_AUTHORIZATION=authorization)

    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=token.key, user=user).exists()


def test_password_change_rejects_inactive_user(client, user, password_change_token):
    user.is_active = False
    user.save(update_fields=["is_active"])
    original_hash = user.password

    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
        format="json",
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()


@pytest.mark.parametrize("method", ["get", "put", "patch", "delete"])
def test_password_change_rejects_unsupported_methods(
    client, user, password_change_token, method
):
    original_hash = user.password
    response = getattr(client, method)(reverse("accounts:password-change"))

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()


def test_password_change_only_changes_authenticated_user(
    client, user, password_change_token
):
    other_user = UserFactory(password=PASSWORD)
    other_token = Token.objects.create(user=other_user)
    other_hash = other_user.password
    original_role = user.role

    response = client.post(
        reverse("accounts:password-change"),
        {
            "current_password": PASSWORD,
            "new_password": NEW_PASSWORD,
            "id": other_user.pk,
            "user": other_user.pk,
            "email": other_user.email,
            "is_superuser": True,
            "role": "admin",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    other_user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert user.role == original_role
    assert not user.is_superuser
    assert other_user.password == other_hash
    assert not Token.objects.filter(user=user).exists()
    assert Token.objects.filter(key=other_token.key, user=other_user).exists()
    client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")
    assert client.get(reverse("accounts:me")).status_code == status.HTTP_200_OK


def test_password_change_preserves_whitespace_in_passwords(client, user):
    current_password = f"  {PASSWORD}  "
    new_password = f"  {NEW_PASSWORD}  "
    user.set_password(current_password)
    user.save(update_fields=["password"])
    token = Token.objects.create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    response = client.post(
        reverse("accounts:password-change"),
        {"current_password": current_password, "new_password": new_password},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    user.refresh_from_db()
    assert user.check_password(new_password)
    assert not user.check_password(new_password.strip())
    assert not Token.objects.filter(user=user).exists()


def test_password_change_rolls_back_when_token_revocation_fails(
    client, user, password_change_token, monkeypatch
):
    original_hash = user.password
    original_delete = QuerySet.delete

    def delete_then_fail(queryset):
        result = original_delete(queryset)
        if queryset.model is Token:
            raise RuntimeError("Falha simulada ao revogar token")
        return result

    monkeypatch.setattr(QuerySet, "delete", delete_then_fail)

    with pytest.raises(RuntimeError, match="Falha simulada ao revogar token"):
        client.post(
            reverse("accounts:password-change"),
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD},
            format="json",
        )

    user.refresh_from_db()
    assert user.password == original_hash
    assert Token.objects.filter(key=password_change_token.key, user=user).exists()
    assert client.get(reverse("accounts:me")).status_code == status.HTTP_200_OK
