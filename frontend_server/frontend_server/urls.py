"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, re_path
from translator import api_views, auth_views, character_views, maps_views
from translator import views as translator_views

urlpatterns = [
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
    path("api/v1/simulations/", api_views.simulations_list, name="api-simulations-list"),
    path("api/v1/simulations/<str:sim_id>/", api_views.simulation_detail, name="api-simulation-detail"),
    path("api/v1/simulations/<str:sim_id>/state/", api_views.simulation_state, name="api-simulation-state"),
    path("api/v1/simulations/<str:sim_id>/agents/", api_views.simulation_agents, name="api-simulation-agents"),
    path(
        "api/v1/simulations/<str:sim_id>/agents/<path:agent_id>/",
        api_views.simulation_agent_detail,
        name="api-simulation-agent-detail",
    ),
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
