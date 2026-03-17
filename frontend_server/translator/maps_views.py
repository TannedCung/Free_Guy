"""
Maps API views.

Endpoints:
  GET /api/v1/maps/  - list all active maps (requires auth)
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from translator.models import Map


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def maps_list(request: Request) -> Response:
    maps = Map.objects.filter(is_active=True).order_by("name")
    data = [
        {
            "id": m.id,
            "name": m.name,
            "description": m.description,
            "preview_image_url": m.preview_image_url,
            "max_agents": m.max_agents,
        }
        for m in maps
    ]
    return Response({"maps": data})
