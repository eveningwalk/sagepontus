from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status


@api_view(["POST"])
@permission_classes([AllowAny])
def email_token_auth(request):
    """이메일 또는 username + password로 DRF Token 반환."""
    identifier = request.data.get("username", "").strip()
    password   = request.data.get("password", "")

    if not identifier or not password:
        return Response(
            {"non_field_errors": ["username/email and password are required."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resolved = identifier
    if "@" in identifier:
        try:
            resolved = User.objects.get(email__iexact=identifier).username
        except User.DoesNotExist:
            pass

    user = authenticate(request, username=resolved, password=password)
    if user is None:
        return Response(
            {"non_field_errors": ["Unable to log in with provided credentials."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key})
