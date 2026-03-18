"""
Authentication API views.

Endpoints:
  POST /api/v1/auth/register/          - register a new user
  POST /api/v1/auth/login/             - login and get JWT tokens
  POST /api/v1/auth/token/refresh/     - refresh access token
  POST /api/v1/auth/logout/            - blacklist refresh token
  GET  /api/v1/auth/me/                - get current user profile
  PATCH /api/v1/auth/me/               - update current user profile
  POST /api/v1/auth/password-reset/    - request password reset
  POST /api/v1/auth/password-reset/confirm/ - confirm password reset
"""

import logging

from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
logger = logging.getLogger(__name__)


def _user_data(user: object) -> dict:
    return {
        "id": user.pk,  # type: ignore[attr-defined]
        "username": user.username,  # type: ignore[attr-defined]
        "email": user.email,  # type: ignore[attr-defined]
    }


def _tokens_for_user(user: object) -> dict:
    refresh = RefreshToken.for_user(user)  # type: ignore[arg-type]
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
    }


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request: Request) -> Response:
    username = request.data.get("username", "").strip()
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")
    password_confirm = request.data.get("password_confirm", "")

    errors: dict = {}

    if not username:
        errors["username"] = ["This field is required."]
    elif User.objects.filter(username=username).exists():
        errors["username"] = ["A user with that username already exists."]

    if not email:
        errors["email"] = ["This field is required."]
    elif User.objects.filter(email=email).exists():
        errors["email"] = ["A user with that email already exists."]

    if not password:
        errors["password"] = ["This field is required."]
    elif password != password_confirm:
        errors["password_confirm"] = ["Passwords do not match."]
    elif len(password) < 8:
        errors["password"] = ["Password must be at least 8 characters."]
    elif password.isdigit():
        errors["password"] = ["Password cannot be entirely numeric."]

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(username=username, email=email, password=password)
    tokens = _tokens_for_user(user)
    return Response(
        {**tokens, "user": _user_data(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request: Request) -> Response:
    username = request.data.get("username", "")
    password = request.data.get("password", "")
    user = authenticate(request=request, username=username, password=password)
    if user is None:
        return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)
    tokens = _tokens_for_user(user)
    return Response({**tokens, "user": _user_data(user)})


@api_view(["POST"])
@permission_classes([AllowAny])
def token_refresh(request: Request) -> Response:
    refresh_token = request.data.get("refresh", "")
    try:
        token = RefreshToken(refresh_token)
        return Response({"access": str(token.access_token)})
    except TokenError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request: Request) -> Response:
    refresh_token = request.data.get("refresh", "")
    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        pass
    return Response(status=status.HTTP_200_OK)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    user = request.user
    if request.method == "GET":
        return Response(
            {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "date_joined": user.date_joined.isoformat(),
            }
        )
    # PATCH
    errors: dict = {}
    new_username = request.data.get("username", None)
    new_email = request.data.get("email", None)

    if new_username is not None:
        new_username = str(new_username).strip()
        if not new_username:
            errors["username"] = ["Username cannot be blank."]
        elif User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
            errors["username"] = ["A user with that username already exists."]
        else:
            user.username = new_username  # type: ignore[attr-defined]

    if new_email is not None:
        new_email = str(new_email).strip()
        if not new_email:
            errors["email"] = ["Email cannot be blank."]
        elif User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            errors["email"] = ["A user with that email already exists."]
        else:
            user.email = new_email  # type: ignore[attr-defined]

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    user.save()  # type: ignore[union-attr]
    return Response(
        {
            "id": user.pk,
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined.isoformat(),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request: Request) -> Response:
    email = request.data.get("email", "").strip()
    # In development, just log the reset link to console (no real email)
    user_qs = User.objects.filter(email=email)
    if user_qs.exists():
        user = user_qs.first()
        # Generate a token for this user (using default token generator)
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        logger.info("Password reset link: /api/v1/auth/password-reset/confirm/?uid=%s&token=%s", uid, token)
    return Response({"detail": "If that email is registered, a reset link has been sent."})


@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request: Request) -> Response:
    from django.contrib.auth.tokens import default_token_generator
    from django.utils.encoding import force_str
    from django.utils.http import urlsafe_base64_decode

    token = request.data.get("token", "")
    uid = request.data.get("uid", "")
    password = request.data.get("password", "")
    password_confirm = request.data.get("password_confirm", "")

    errors: dict = {}

    if password != password_confirm:
        errors["password_confirm"] = ["Passwords do not match."]
    elif len(password) < 8:
        errors["password"] = ["Password must be at least 8 characters."]
    elif password.isdigit():
        errors["password"] = ["Password cannot be entirely numeric."]

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=user_id)
    except (User.DoesNotExist, ValueError, TypeError):
        return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

    if not default_token_generator.check_token(user, token):
        return Response({"detail": "Token is invalid or expired."}, status=status.HTTP_400_BAD_REQUEST)

    user.set_password(password)
    user.save()
    return Response({"detail": "Password has been reset successfully."})
