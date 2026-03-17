"""
Simulation management API views.

Endpoints:
  POST   /api/v1/simulations/{sim_id}/drop/            - drop a character into simulation
  POST   /api/v1/simulations/{sim_id}/start/           - start simulation
  POST   /api/v1/simulations/{sim_id}/pause/           - pause simulation
  POST   /api/v1/simulations/{sim_id}/resume/          - resume simulation
  PATCH  /api/v1/simulations/{sim_id}/                 - update visibility (admin only)
  GET    /api/v1/simulations/mine/                     - list user's simulations
  GET    /api/v1/simulations/public/                   - list public simulations
  POST   /api/v1/simulations/{sim_id}/members/         - invite user to simulation
  GET    /api/v1/simulations/{sim_id}/members/         - list members
  DELETE /api/v1/simulations/{sim_id}/members/{uid}/   - remove member
  GET    /api/v1/invites/                              - list pending invites
  POST   /api/v1/invites/{mid}/accept/                 - accept invite
  POST   /api/v1/invites/{mid}/decline/                - decline invite
"""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from translator.api_views import _sim_summary_from_orm
from translator.models import Character, Persona, Simulation, SimulationMembership

User = get_user_model()


def _get_simulation(sim_id: str) -> Simulation | None:
    try:
        return Simulation.objects.get(name=sim_id)
    except Simulation.DoesNotExist:
        return None


def _is_admin(sim: Simulation, user: object) -> bool:
    return SimulationMembership.objects.filter(
        simulation=sim,
        user=user,
        role=SimulationMembership.Role.ADMIN,
        status=SimulationMembership.MemberStatus.ACTIVE,
    ).exists()


def _can_observe(sim: Simulation, user: object) -> bool:
    if sim.visibility == Simulation.Visibility.PUBLIC:
        return True
    return SimulationMembership.objects.filter(
        simulation=sim,
        user=user,
        status=SimulationMembership.MemberStatus.ACTIVE,
    ).exists()


# ---------------------------------------------------------------------------
# US-012: Drop character into simulation
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def drop_character(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can drop characters."}, status=status.HTTP_403_FORBIDDEN)

    char_id = request.data.get("character_id")
    if char_id is None:
        return Response({"detail": "character_id is required."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        char = Character.objects.get(pk=char_id)
    except Character.DoesNotExist:
        return Response({"detail": "Character not found."}, status=status.HTTP_404_NOT_FOUND)

    if char.owner != request.user:
        return Response({"detail": "Character does not belong to you."}, status=status.HTTP_400_BAD_REQUEST)

    if char.status == Character.Status.IN_SIMULATION:
        return Response({"detail": "Character is already in a simulation."}, status=status.HTTP_400_BAD_REQUEST)

    # Create Persona from character fields
    Persona.objects.get_or_create(
        simulation=sim,
        name=char.name,
        defaults={
            "first_name": char.name.split()[0] if " " in char.name else char.name,
            "last_name": char.name.split()[-1] if " " in char.name else "",
            "age": char.age,
            "innate": char.traits,
            "learned": char.backstory,
            "currently": char.currently,
            "lifestyle": char.lifestyle,
            "daily_plan_req": char.daily_plan,
        },
    )

    char.status = Character.Status.IN_SIMULATION
    char.simulation = sim
    char.save(update_fields=["status", "simulation"])

    return Response(_sim_summary_from_orm(sim))


# ---------------------------------------------------------------------------
# US-013: Start, pause, resume simulation
# ---------------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_simulation(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can start a simulation."}, status=status.HTTP_403_FORBIDDEN)

    if sim.status == Simulation.Status.RUNNING:
        return Response({"detail": "Simulation is already running."}, status=status.HTTP_409_CONFLICT)

    if not sim.personas.exists():
        return Response(
            {"detail": "No characters have been dropped into this simulation."}, status=status.HTTP_400_BAD_REQUEST
        )

    if sim.start_date is None:
        sim.start_date = timezone.now()
    sim.status = Simulation.Status.RUNNING
    sim.save(update_fields=["status", "start_date"])

    return Response(_sim_summary_from_orm(sim))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pause_simulation(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can pause a simulation."}, status=status.HTTP_403_FORBIDDEN)

    if sim.status != Simulation.Status.RUNNING:
        return Response({"detail": "Simulation is not running."}, status=status.HTTP_409_CONFLICT)

    sim.status = Simulation.Status.PAUSED
    sim.save(update_fields=["status"])

    return Response(_sim_summary_from_orm(sim))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resume_simulation(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can resume a simulation."}, status=status.HTTP_403_FORBIDDEN)

    if sim.status != Simulation.Status.PAUSED:
        return Response({"detail": "Simulation is not paused."}, status=status.HTTP_409_CONFLICT)

    sim.status = Simulation.Status.RUNNING
    sim.save(update_fields=["status"])

    return Response(_sim_summary_from_orm(sim))


# ---------------------------------------------------------------------------
# US-014: Access control and visibility
# ---------------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_simulations(request: Request) -> Response:
    memberships = SimulationMembership.objects.filter(
        user=request.user, status=SimulationMembership.MemberStatus.ACTIVE
    ).select_related("simulation")
    sims = [_sim_summary_from_orm(m.simulation) for m in memberships]
    return Response({"simulations": sims})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def public_simulations(request: Request) -> Response:
    qs = Simulation.objects.filter(visibility=Simulation.Visibility.PUBLIC)
    sim_status = request.query_params.get("status")
    if sim_status:
        qs = qs.filter(status=sim_status)
    return Response({"simulations": [_sim_summary_from_orm(s) for s in qs]})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_simulation(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can update settings."}, status=status.HTTP_403_FORBIDDEN)

    if "visibility" in request.data:
        visibility = request.data["visibility"]
        valid = [c[0] for c in Simulation.Visibility.choices]
        if visibility not in valid:
            return Response(
                {"visibility": [f"Must be one of: {', '.join(valid)}."]}, status=status.HTTP_400_BAD_REQUEST
            )
        sim.visibility = visibility
        sim.save(update_fields=["visibility"])

    return Response(_sim_summary_from_orm(sim))


# ---------------------------------------------------------------------------
# US-015: Simulation invite system
# ---------------------------------------------------------------------------


def _member_data(m: SimulationMembership) -> dict:
    return {
        "id": m.pk,
        "user_id": m.user_id,
        "username": m.user.username,
        "role": m.role,
        "status": m.status,
        "invited_at": m.invited_at.isoformat(),
        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def simulation_members(request: Request, sim_id: str) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        if not _can_observe(sim, request.user):
            return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        members = SimulationMembership.objects.filter(simulation=sim).select_related("user")
        return Response({"members": [_member_data(m) for m in members]})

    # POST — invite user
    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can invite users."}, status=status.HTTP_403_FORBIDDEN)

    username = str(request.data.get("username", "")).strip()
    if not username:
        return Response({"username": ["This field is required."]}, status=status.HTTP_400_BAD_REQUEST)

    try:
        invited_user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    if SimulationMembership.objects.filter(simulation=sim, user=invited_user).exists():
        return Response({"detail": "User is already a member."}, status=status.HTTP_409_CONFLICT)

    membership = SimulationMembership.objects.create(
        simulation=sim,
        user=invited_user,
        role=SimulationMembership.Role.OBSERVER,
        status=SimulationMembership.MemberStatus.INVITED,
    )
    return Response(_member_data(membership), status=status.HTTP_201_CREATED)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def remove_member(request: Request, sim_id: str, user_id: int) -> Response:
    sim = _get_simulation(sim_id)
    if sim is None:
        return Response({"detail": f"Simulation '{sim_id}' not found."}, status=status.HTTP_404_NOT_FOUND)

    if not _is_admin(sim, request.user):
        return Response({"detail": "Only simulation admins can remove members."}, status=status.HTTP_403_FORBIDDEN)

    try:
        membership = SimulationMembership.objects.get(simulation=sim, user_id=user_id)
    except SimulationMembership.DoesNotExist:
        return Response({"detail": "Member not found."}, status=status.HTTP_404_NOT_FOUND)

    membership.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_invites(request: Request) -> Response:
    memberships = SimulationMembership.objects.filter(
        user=request.user, status=SimulationMembership.MemberStatus.INVITED
    ).select_related("simulation", "simulation__owner")
    return Response({"invites": [_member_data(m) for m in memberships]})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept_invite(request: Request, membership_id: int) -> Response:
    try:
        membership = SimulationMembership.objects.get(pk=membership_id, user=request.user)
    except SimulationMembership.DoesNotExist:
        return Response({"detail": "Invite not found."}, status=status.HTTP_404_NOT_FOUND)

    membership.status = SimulationMembership.MemberStatus.ACTIVE
    membership.joined_at = timezone.now()
    membership.save(update_fields=["status", "joined_at"])
    return Response(_member_data(membership))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decline_invite(request: Request, membership_id: int) -> Response:
    try:
        membership = SimulationMembership.objects.get(pk=membership_id, user=request.user)
    except SimulationMembership.DoesNotExist:
        return Response({"detail": "Invite not found."}, status=status.HTTP_404_NOT_FOUND)

    membership.status = SimulationMembership.MemberStatus.DECLINED
    membership.save(update_fields=["status"])
    return Response(_member_data(membership))
