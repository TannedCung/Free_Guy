"""
ASGI config for frontend_server project.

Exposes the ASGI callable as module-level variable named ``application``.
Routes HTTP to Django and (when ENABLE_CHANNELS != 'false') WebSocket to
SimulationConsumer.

Set ENABLE_CHANNELS=false on Vercel where Channels is replaced by the SSE
Edge Function and WebSocket support is not available.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frontend_server.settings")

_enable_channels = os.environ.get("ENABLE_CHANNELS", "true").lower() != "false"

if _enable_channels:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.urls import path

    from translator.consumers import SimulationConsumer  # noqa: E402

    websocket_urlpatterns = [
        path("ws/simulations/<str:sim_id>/", SimulationConsumer.as_asgi()),
    ]

    application = ProtocolTypeRouter(
        {
            "http": get_asgi_application(),
            "websocket": URLRouter(websocket_urlpatterns),
        }
    )
else:
    # WSGI-only mode (Vercel): no WebSocket support; use SSE Edge Function instead.
    application = get_asgi_application()
