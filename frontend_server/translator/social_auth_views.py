"""
Social authentication views.

Provides OAuth initiation endpoints for Google and GitHub.
Uses django-allauth for provider configuration.

Endpoints:
  GET /api/v1/auth/social/google/   - redirect to Google OAuth
  GET /api/v1/auth/social/github/   - redirect to GitHub OAuth
"""

from django.shortcuts import redirect
from django.urls import reverse


def social_login_google(request):
    """Redirect to django-allauth Google login URL."""
    return redirect(reverse("google_login"))


def social_login_github(request):
    """Redirect to django-allauth GitHub login URL."""
    return redirect(reverse("github_login"))
