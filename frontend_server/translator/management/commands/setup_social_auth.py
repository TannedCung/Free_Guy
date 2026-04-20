"""
Management command to set up social authentication providers.

Creates or updates SocialApp entries for Google and GitHub OAuth
using credentials from environment variables.
"""

import os

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Set up social authentication providers from environment variables"

    def handle(self, *args, **options):
        # Update the Site domain from DJANGO_SITE_DOMAIN if set, so allauth
        # builds the correct redirect_uri for OAuth providers.
        site_domain = os.environ.get("DJANGO_SITE_DOMAIN", "")
        site = Site.objects.get_current()
        if site_domain and site.domain != site_domain:
            site.domain = site_domain
            site.name = site_domain
            site.save()
            self.stdout.write(self.style.SUCCESS(f"✓ Site domain updated to: {site_domain}"))

        self.stdout.write(f"Configuring social auth for site: {site.domain}")

        # Google OAuth
        google_client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
        google_client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")

        if google_client_id and google_client_secret:
            google_app, created = SocialApp.objects.get_or_create(
                provider="google",
                defaults={
                    "name": "Google",
                    "client_id": google_client_id,
                    "secret": google_client_secret,
                },
            )
            if not created:
                google_app.client_id = google_client_id
                google_app.secret = google_client_secret
                google_app.save()

            google_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f"✓ Google OAuth configured (created={created})"))
        else:
            self.stdout.write(
                self.style.WARNING("⚠ Google OAuth skipped (GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET not set)")
            )

        # GitHub OAuth
        github_client_id = os.environ.get("GITHUB_CLIENT_ID", "")
        github_client_secret = os.environ.get("GITHUB_CLIENT_SECRET", "")

        if github_client_id and github_client_secret and github_client_id != "your-github-client-id-here":
            github_app, created = SocialApp.objects.get_or_create(
                provider="github",
                defaults={
                    "name": "GitHub",
                    "client_id": github_client_id,
                    "secret": github_client_secret,
                },
            )
            if not created:
                github_app.client_id = github_client_id
                github_app.secret = github_client_secret
                github_app.save()

            github_app.sites.add(site)
            self.stdout.write(self.style.SUCCESS(f"✓ GitHub OAuth configured (created={created})"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    "⚠ GitHub OAuth skipped (GITHUB_CLIENT_ID or GITHUB_CLIENT_SECRET not set or placeholder)"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nSocial auth setup complete!"))
