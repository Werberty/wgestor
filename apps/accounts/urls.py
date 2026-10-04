from django.urls import path
from .views import PasswordResetRequestAPI

urlpatterns = [
    path("api/password-reset", PasswordResetRequestAPI.as_view(), name="password-reset"),
]
