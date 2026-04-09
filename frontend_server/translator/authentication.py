"""
Custom DRF authentication: reads JWT from httpOnly cookie 'access_token'.
Falls back to the Authorization header so non-browser clients (curl, scripts)
still work unchanged.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import TokenError

AUTH_COOKIE_ACCESS = "access_token"


class JWTCookieAuthentication(JWTAuthentication):
    """Authenticate via httpOnly 'access_token' cookie or Authorization header."""

    def authenticate(self, request):
        raw_token = request.COOKIES.get(AUTH_COOKIE_ACCESS)
        if raw_token is None:
            # No cookie — fall back to "Authorization: Bearer …" header
            return super().authenticate(request)
        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError:
            return None
        return self.get_user(validated_token), validated_token
