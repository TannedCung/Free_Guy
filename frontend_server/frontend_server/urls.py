"""frontend_server URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
"""

from django.contrib import admin
from django.urls import path, re_path
from translator import api_views
from translator import views as translator_views

urlpatterns = [
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
