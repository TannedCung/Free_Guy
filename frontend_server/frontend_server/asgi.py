"""
ASGI config for frontend_server project.

Exposes the ASGI callable as module-level variable named ``application``.
Routes HTTP to Django and WebSocket to SimulationConsumer.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frontend_server.settings")

# Import consumer here (must be after Django setup)
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
