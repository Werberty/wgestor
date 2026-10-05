import pytest
from http import HTTPStatus
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.core import mail


@pytest.mark.django_db
def test_password_reset_request_send_email(client, user):
    response = client.post(
        '/accounts/api/password-reset',
        data={'email': user.email}
    )
    
    assert response.status_code == HTTPStatus.OK
    assert len(mail.outbox) == 1
    assert user.email in mail.outbox[0].to


@pytest.mark.django_db
def test_password_reset_request_does_not_reveal_non_existent_emails(client):
    response = client.post(
        '/accounts/api/password-reset',
        data={'email': 'non.existent@email.com'}
    )

    assert response.status_code == HTTPStatus.OK
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_password_reset_confirm_changes_successfuly(client, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = PasswordResetTokenGenerator().make_token(user)

    new_password = '12345678'
    response = client.post(
        '/accounts/api/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.check_password(new_password)


@pytest.mark.django_db
@pytest.mark.parametrize("token", ["token_invalido", "", "abc123789"])
def test_password_reset_confirm_invalid_token(client, user, token):
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    new_password = '12345678'
    response = client.post(
        '/accounts/api/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )
    
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_password_reset_confirm_invalid_link(client):
    uid = 'uid_invalid'
    token = 'token_invalid'

    new_password = '12345678'
    response = client.post(
        '/accounts/api/password-reset/confirm',
        data={
            'uidb64': uid, 'token': token, 'new_password': new_password
        }
    )
    
    assert response.status_code == HTTPStatus.BAD_REQUEST
