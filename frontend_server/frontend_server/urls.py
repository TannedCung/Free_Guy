"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from translator import api_views, auth_views, character_views, maps_views, simulation_views, social_auth_views
from translator import views as translator_views


def health_check(request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", health_check, name="health-check"),
    # django-allauth social auth URLs (required for allauth's OAuth flow)
    path("accounts/", include("allauth.urls")),
    # REST API v1 — social login redirect endpoints
    path("api/v1/auth/social/google/", social_auth_views.social_login_google, name="api-social-google"),
    path("api/v1/auth/social/github/", social_auth_views.social_login_github, name="api-social-github"),
    # OAuth callback: allauth → JWT cookies → redirect to SPA (LOGIN_REDIRECT_URL)
    path("api/v1/auth/social/callback/", social_auth_views.oauth_complete, name="api-social-callback"),
    # REST API v1 — auth endpoints
    path("api/v1/auth/register/", auth_views.register, name="api-auth-register"),
    path("api/v1/auth/login/", auth_views.login_view, name="api-auth-login"),
    path("api/v1/auth/token/refresh/", auth_views.token_refresh, name="api-auth-token-refresh"),
    path("api/v1/auth/logout/", auth_views.logout_view, name="api-auth-logout"),
    path("api/v1/auth/me/", auth_views.me, name="api-auth-me"),
    path("api/v1/auth/password-reset/", auth_views.password_reset, name="api-auth-password-reset"),
    path(
        "api/v1/auth/password-reset/confirm/", auth_views.password_reset_confirm, name="api-auth-password-reset-confirm"
    ),
    # REST API v1 — character endpoints
    path("api/v1/characters/", character_views.characters_list, name="api-characters-list"),
    path("api/v1/characters/<int:char_id>/", character_views.character_detail, name="api-character-detail"),
    # REST API v1 — maps endpoints
    path("api/v1/maps/", maps_views.maps_list, name="api-maps-list"),
    # REST API v1 — simulation endpoints
    path("api/v1/simulations/mine/", simulation_views.my_simulations, name="api-simulations-mine"),
    path("api/v1/simulations/public/", simulation_views.public_simulations, name="api-simulations-public"),
    path("api/v1/simulations/", api_views.simulations_list, name="api-simulations-list"),
    path("api/v1/simulations/<str:sim_id>/drop/", simulation_views.drop_character, name="api-simulation-drop"),
    path("api/v1/simulations/<str:sim_id>/start/", simulation_views.start_simulation, name="api-simulation-start"),
    path("api/v1/simulations/<str:sim_id>/pause/", simulation_views.pause_simulation, name="api-simulation-pause"),
    path("api/v1/simulations/<str:sim_id>/resume/", simulation_views.resume_simulation, name="api-simulation-resume"),
    path(
        "api/v1/simulations/<str:sim_id>/members/", simulation_views.simulation_members, name="api-simulation-members"
    ),
    path(
        "api/v1/simulations/<str:sim_id>/members/<int:user_id>/",
        simulation_views.remove_member,
        name="api-simulation-remove-member",
    ),
    path("api/v1/simulations/<str:sim_id>/", api_views.simulation_detail, name="api-simulation-detail"),
    path("api/v1/simulations/<str:sim_id>/state/", api_views.simulation_state, name="api-simulation-state"),
    path("api/v1/simulations/<str:sim_id>/agents/", api_views.simulation_agents, name="api-simulation-agents"),
    path(
        "api/v1/simulations/<str:sim_id>/agents/<path:agent_id>/",
        api_views.simulation_agent_detail,
        name="api-simulation-agent-detail",
    ),
    # REST API v1 — replay endpoints
    path("api/v1/simulations/<str:sim_id>/replay/", simulation_views.replay_meta, name="api-replay-meta"),
    path("api/v1/simulations/<str:sim_id>/replay/<int:step>/", simulation_views.replay_step, name="api-replay-step"),
    # REST API v1 — debug endpoint
    path("api/v1/simulations/<str:sim_id>/debug/", api_views.simulation_debug_step, name="api-simulation-debug"),
    # REST API v1 — SSE polling endpoint (used by Vercel Edge Function stream)
    path(
        "api/v1/simulations/<str:sim_id>/movements/latest/",
        api_views.simulation_latest_movement,
        name="api-simulation-latest-movement",
    ),
    # SSE stream — replaces Vercel Edge Function for self-hosted deployments
    path(
        "api/simulations/<str:sim_id>/stream",
        api_views.simulation_sse_stream,
        name="api-simulation-sse-stream",
    ),
    # REST API v1 — simulation step stage endpoints (Vercel serverless microservices)
    path(
        "api/v1/simulations/<str:sim_id>/step/perceive/", api_views.simulation_step_perceive, name="api-step-perceive"
    ),
    path(
        "api/v1/simulations/<str:sim_id>/step/retrieve/", api_views.simulation_step_retrieve, name="api-step-retrieve"
    ),
    path("api/v1/simulations/<str:sim_id>/step/plan/", api_views.simulation_step_plan, name="api-step-plan"),
    path("api/v1/simulations/<str:sim_id>/step/reflect/", api_views.simulation_step_reflect, name="api-step-reflect"),
    path("api/v1/simulations/<str:sim_id>/step/execute/", api_views.simulation_step_execute, name="api-step-execute"),
    # REST API v1 — invite endpoints
    path("api/v1/invites/", simulation_views.my_invites, name="api-invites-list"),
    path("api/v1/invites/<int:membership_id>/accept/", simulation_views.accept_invite, name="api-invite-accept"),
    path("api/v1/invites/<int:membership_id>/decline/", simulation_views.decline_invite, name="api-invite-decline"),
    # REST API v1 — demo endpoints
    path("api/v1/demos/", api_views.demos_list, name="api-demos-list"),
    path("api/v1/demos/<str:demo_id>/step/<int:step>/", api_views.demo_step, name="api-demo-step"),
    # Legacy game-loop endpoints (used by Phaser canvas via XHR)
    re_path(r"^process_environment/$", translator_views.process_environment, name="process_environment"),
    re_path(r"^update_environment/$", translator_views.update_environment, name="update_environment"),
    re_path(r"^path_tester_update/$", translator_views.path_tester_update, name="path_tester_update"),
    # Django admin
    path("admin/", admin.site.urls),
    # Catch-all: serve React SPA index.html for client-side routing.
    # Must be last — matches everything not handled above.
    re_path(r"^.*$", translator_views.spa_index, name="spa"),
]
