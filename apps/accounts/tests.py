import pytest
from http import HTTPStatus
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
