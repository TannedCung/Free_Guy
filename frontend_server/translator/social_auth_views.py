"""
Social authentication views.

Provides OAuth initiation endpoints for Google and GitHub, plus the
post-OAuth callback that converts the allauth session into httpOnly JWT cookies.

Endpoints:
  GET  /api/v1/auth/social/google/    - redirect to Google OAuth
  GET  /api/v1/auth/social/github/    - redirect to GitHub OAuth
  GET  /api/v1/auth/social/callback/  - exchange allauth session → JWT cookies
"""

from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from .auth_views import _set_auth_cookies


def social_login_google(request):
    """Redirect to django-allauth Google login URL."""
    return redirect(reverse("google_login"))


def social_login_github(request):
    """Redirect to django-allauth GitHub login URL."""
    return redirect(reverse("github_login"))


def oauth_complete(request):
    """
    Called by allauth (via LOGIN_REDIRECT_URL) after a successful OAuth flow.

    At this point Django's session middleware has already authenticated the user
    from the allauth session cookie, so request.user is populated.  We:
      1. Issue JWT tokens for the user
      2. Set them as httpOnly cookies on the redirect response
      3. Log out of the Django session (we don't need it any more)
      4. Send the browser to the React SPA root
    """
    if not request.user.is_authenticated:
        return redirect("/login?error=oauth_failed")

    user = request.user
    refresh = RefreshToken.for_user(user)
    access_token = str(refresh.access_token)
    refresh_token = str(refresh)

    # Destroy the allauth session — JWT cookies take over from here.
    auth_logout(request)

    response = redirect("/dashboard")
    _set_auth_cookies(response, access_token=access_token, refresh_token=refresh_token)
    return response
