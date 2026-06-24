from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


def authenticate_by_email(request, email, password):
    """이메일(대소문자 무시) + password 로 인증.

    동일 이메일을 가진 계정이 여러 개여도 안전하게 처리한다.
    (Django 기본 User 는 username 으로 인증하므로 email→username 으로 해석)
    각 후보 계정에 대해 password 가 맞는 계정을 반환한다.
    """
    email    = (email or "").strip()
    password = password or ""
    if not email or not password:
        return None

    for account in User.objects.filter(email__iexact=email):
        user = authenticate(request, username=account.username, password=password)
        if user is not None:
            return user
    return None


@api_view(["POST"])
@permission_classes([AllowAny])
def email_token_auth(request):
    """이메일 + password 로 DRF Token 반환 (email-only)."""
    # `email` 키를 우선 사용. 구버전 클라이언트 호환을 위해 `username` 키도 이메일로 취급.
    email    = (request.data.get("email") or request.data.get("username") or "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"non_field_errors": ["Email and password are required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate_by_email(request, email, password)
    if user is None:
        return Response(
            {"non_field_errors": ["Unable to log in with provided credentials."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key})
