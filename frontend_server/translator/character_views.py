"""
Character CRUD API views.

Endpoints:
  GET    /api/v1/characters/          - list authenticated user's characters
  POST   /api/v1/characters/          - create a new character
  GET    /api/v1/characters/{id}/     - get character detail
  PATCH  /api/v1/characters/{id}/     - update character
  DELETE /api/v1/characters/{id}/     - delete character
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from translator.models import Character


def _character_data(char: Character) -> dict:
    return {
        "id": char.pk,
        "name": char.name,
        "age": char.age,
        "traits": char.traits,
        "backstory": char.backstory,
        "currently": char.currently,
        "lifestyle": char.lifestyle,
        "daily_plan": char.daily_plan,
        "status": char.status,
        "simulation": char.simulation_id,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def characters_list(request: Request) -> Response:
    if request.method == "GET":
        chars = Character.objects.filter(owner=request.user).order_by("name")
        return Response({"characters": [_character_data(c) for c in chars]})

    # POST
    name = str(request.data.get("name", "")).strip()
    if not name:
        return Response({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

    if Character.objects.filter(owner=request.user, name=name).exists():
        return Response({"name": ["You already have a character with that name."]}, status=status.HTTP_400_BAD_REQUEST)

    age_raw = request.data.get("age", None)
    age = None
    if age_raw is not None:
        try:
            age = int(age_raw)
        except (ValueError, TypeError):
            return Response({"age": ["Must be a valid integer."]}, status=status.HTTP_400_BAD_REQUEST)

    char = Character.objects.create(
        owner=request.user,
        name=name,
        age=age,
        traits=request.data.get("traits", ""),
        backstory=request.data.get("backstory", ""),
        currently=request.data.get("currently", ""),
        lifestyle=request.data.get("lifestyle", ""),
        daily_plan=request.data.get("daily_plan", ""),
    )
    return Response(_character_data(char), status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def character_detail(request: Request, char_id: int) -> Response:
    try:
        char = Character.objects.get(pk=char_id, owner=request.user)
    except Character.DoesNotExist:
        # Check if it exists at all to distinguish 404 vs 403
        if Character.objects.filter(pk=char_id).exists():
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        return Response(_character_data(char))

    if request.method == "DELETE":
        if char.status == Character.Status.IN_SIMULATION:
            return Response(
                {"detail": "Cannot delete a character that is currently in a simulation."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        char.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PATCH
    if char.status == Character.Status.IN_SIMULATION:
        return Response(
            {"detail": "Cannot edit a character that is currently in a simulation."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "name" in request.data:
        new_name = str(request.data["name"]).strip()
        if not new_name:
            return Response({"name": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)
        if Character.objects.filter(owner=request.user, name=new_name).exclude(pk=char.pk).exists():
            return Response(
                {"name": ["You already have a character with that name."]}, status=status.HTTP_400_BAD_REQUEST
            )
        char.name = new_name

    for field in ("traits", "backstory", "currently", "lifestyle", "daily_plan"):
        if field in request.data:
            setattr(char, field, request.data[field])

    if "age" in request.data:
        age_raw = request.data["age"]
        if age_raw is None:
            char.age = None
        else:
            try:
                char.age = int(age_raw)
            except (ValueError, TypeError):
                return Response({"age": ["Must be a valid integer."]}, status=status.HTTP_400_BAD_REQUEST)

    char.save()
    return Response(_character_data(char))
