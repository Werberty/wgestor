from django.shortcuts import render
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.serializers import PasswordResetRequestSerializer
from apps.accounts.models import User
from config import settings


class PasswordResetRequestAPI(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']
        user = User.objects.filter(email=email).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = PasswordResetTokenGenerator().make_token(user)
            reset_link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Redefinição de senha",
                message=f"Clique no link para redefinir sua senha: {reset_link}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
            )
        
        return Response(
            {"detail": "Se o e-mail existir, enviaremos instruções."},
            status=status.HTTP_200_OK,
        )
