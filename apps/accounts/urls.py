from django.urls import path
from .views import PasswordResetRequestAPI, PasswordResetConfirmAPI

urlpatterns = [
    path("password-reset", PasswordResetRequestAPI.as_view(), name="password-reset"),
    path("password-reset/confirm", PasswordResetConfirmAPI.as_view(), name="password-reset-confirm"),
]
