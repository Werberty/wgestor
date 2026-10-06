from django.urls import path

from .views import (
    LoginView, LogoutView, MeView, 
    PasswordResetRequestAPI, PasswordResetConfirmAPI
)


app_name = "accounts"


urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('me/', MeView.as_view(), name='me'),
    path("password-reset", PasswordResetRequestAPI.as_view(), name="password-reset"),
    path("password-reset/confirm", PasswordResetConfirmAPI.as_view(), name="password-reset-confirm"),
]

