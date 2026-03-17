"""
Django REST Framework API views for simulation and demo endpoints.

Endpoints:
  GET  /api/v1/simulations/                        - list all simulations
  POST /api/v1/simulations/                        - create or fork a simulation
  GET  /api/v1/simulations/:id/                    - get simulation details
  GET  /api/v1/simulations/:id/state/              - get current world state
  GET  /api/v1/simulations/:id/agents/             - list agents with current state
  GET  /api/v1/simulations/:id/agents/:agent_id/   - get detailed agent state
  GET  /api/v1/demos/                              - list available demos
  GET  /api/v1/demos/:id/step/:step/               - get demo data for a step
"""

import string

import qdrant_utils
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from translator.models import (
    ConceptNode,
    Demo,
    DemoMovement,
    EnvironmentState,
    KeywordStrength,
    Map,
    Persona,
    PersonaScratch,
    Simulation,
    SimulationMembership,
    SpatialMemory,
)

# ---------------------------------------------------------------------------
# DB-based helpers
# ---------------------------------------------------------------------------


def _sim_summary_from_orm(sim: Simulation) -> dict:
    """Return summary dict from a Simulation ORM object."""
    persona_names = list(sim.personas.values_list("name", flat=True))
    return {
        "id": sim.name,
        "name": sim.name,
        "fork_sim_code": sim.fork_sim_code,
        "start_date": sim.start_date.isoformat() if sim.start_date else None,
        "curr_time": sim.curr_time.isoformat() if sim.curr_time else None,
        "sec_per_step": sim.sec_per_step,
        "maze_name": sim.maze_name,
        "persona_names": persona_names,
        "step": sim.step,
        "map_id": sim.map_id_id,
        "visibility": sim.visibility,
        "owner": sim.owner_id,
        "status": sim.status,
    }


def _fork_simulation(src_name: str, new_name: str) -> Simulation:
    """Deep-copy a simulation including all personas, memory, and Qdrant embeddings."""
    src_sim = Simulation.objects.get(name=src_name)
    with transaction.atomic():
        new_sim = Simulation.objects.create(
            name=new_name,
            description=src_sim.description,
            status=Simulation.Status.PENDING,
            fork_sim_code=src_name,
            start_date=src_sim.start_date,
            curr_time=src_sim.curr_time,
            sec_per_step=src_sim.sec_per_step,
            maze_name=src_sim.maze_name,
            step=src_sim.step,
            config=src_sim.config,
        )
        for persona in src_sim.personas.all():
            old_pk = persona.pk
            new_persona = Persona.objects.create(
                simulation=new_sim,
                name=persona.name,
                first_name=persona.first_name,
                last_name=persona.last_name,
                age=persona.age,
                innate=persona.innate,
                learned=persona.learned,
                currently=persona.currently,
                lifestyle=persona.lifestyle,
                living_area=persona.living_area,
                daily_plan_req=persona.daily_plan_req,
                status=persona.status,
            )
            # Copy PersonaScratch
            try:
                s = PersonaScratch.objects.get(persona=persona)
                PersonaScratch.objects.create(
                    persona=new_persona,
                    vision_r=s.vision_r,
                    att_bandwidth=s.att_bandwidth,
                    retention=s.retention,
                    curr_time=s.curr_time,
                    curr_tile=s.curr_tile,
                    concept_forget=s.concept_forget,
                    daily_reflection_time=s.daily_reflection_time,
                    daily_reflection_size=s.daily_reflection_size,
                    overlap_reflect_th=s.overlap_reflect_th,
                    kw_strg_event_reflect_th=s.kw_strg_event_reflect_th,
                    kw_strg_thought_reflect_th=s.kw_strg_thought_reflect_th,
                    recency_w=s.recency_w,
                    relevance_w=s.relevance_w,
                    importance_w=s.importance_w,
                    recency_decay=s.recency_decay,
                    importance_trigger_max=s.importance_trigger_max,
                    importance_trigger_curr=s.importance_trigger_curr,
                    importance_ele_n=s.importance_ele_n,
                    thought_count=s.thought_count,
                    daily_req=s.daily_req,
                    f_daily_schedule=s.f_daily_schedule,
                    f_daily_schedule_hourly_org=s.f_daily_schedule_hourly_org,
                    act_address=s.act_address,
                    act_start_time=s.act_start_time,
                    act_duration=s.act_duration,
                    act_description=s.act_description,
                    act_pronunciatio=s.act_pronunciatio,
                    act_event=s.act_event,
                    act_obj_description=s.act_obj_description,
                    act_obj_pronunciatio=s.act_obj_pronunciatio,
                    act_obj_event=s.act_obj_event,
                    chatting_with=s.chatting_with,
                    chat=s.chat,
                    chatting_with_buffer=s.chatting_with_buffer,
                    chatting_end_time=s.chatting_end_time,
                    act_path_set=s.act_path_set,
                    planned_path=s.planned_path,
                )
            except PersonaScratch.DoesNotExist:
                pass
            # Copy SpatialMemory
            try:
                sm = SpatialMemory.objects.get(persona=persona)
                SpatialMemory.objects.create(persona=new_persona, tree=sm.tree)
            except SpatialMemory.DoesNotExist:
                pass
            # Bulk copy ConceptNodes
            src_nodes = list(ConceptNode.objects.filter(persona=persona))
            if src_nodes:
                ConceptNode.objects.bulk_create(
                    [
                        ConceptNode(
                            persona=new_persona,
                            node_id=n.node_id,
                            node_count=n.node_count,
                            type_count=n.type_count,
                            node_type=n.node_type,
                            depth=n.depth,
                            created=n.created,
                            expiration=n.expiration,
                            last_accessed=n.last_accessed,
                            subject=n.subject,
                            predicate=n.predicate,
                            object=n.object,
                            description=n.description,
                            embedding_key=n.embedding_key,
                            poignancy=n.poignancy,
                            keywords=n.keywords,
                            filling=n.filling,
                        )
                        for n in src_nodes
                    ]
                )
            # Bulk copy KeywordStrengths
            src_kws = list(KeywordStrength.objects.filter(persona=persona))
            if src_kws:
                KeywordStrength.objects.bulk_create(
                    [
                        KeywordStrength(
                            persona=new_persona,
                            keyword=kw.keyword,
                            strength_type=kw.strength_type,
                            strength=kw.strength,
                        )
                        for kw in src_kws
                    ]
                )
            # Copy Qdrant embeddings
            qdrant_utils.copy_persona_embeddings(old_pk, new_persona.pk, new_sim.pk)
    return new_sim


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def simulations_list(request: Request) -> Response:
    """
    GET  - list all available simulations.
    POST - create a new simulation or fork from an existing one.
    """
    if request.method == "GET":
        sims = [_sim_summary_from_orm(s) for s in Simulation.objects.all()]
        return Response({"simulations": sims})

    # POST — create or fork
    sim_name: str = request.data.get("name", "").strip()
    fork_from: str = request.data.get("fork_from", "").strip()
    map_id_val: str = request.data.get("map_id", "the_ville").strip() or "the_ville"
    visibility_val: str = request.data.get("visibility", Simulation.Visibility.PRIVATE)

    if not sim_name:
        return Response(
            {"error": "name is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Sanitise: allow alphanumerics, hyphens, underscores
    allowed = set(string.ascii_letters + string.digits + "-_")
    if not all(c in allowed for c in sim_name):
        return Response(
            {"error": "name may only contain letters, digits, hyphens, and underscores"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if Simulation.objects.filter(name=sim_name).exists():
        return Response(
            {"error": f"simulation '{sim_name}' already exists"},
            status=status.HTTP_409_CONFLICT,
        )

    # Validate map_id
    try:
        map_obj = Map.objects.get(pk=map_id_val)
    except Map.DoesNotExist:
        return Response(
            {"error": f"map '{map_id_val}' not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if fork_from:
        if not Simulation.objects.filter(name=fork_from).exists():
            return Response(
                {"error": f"fork_from simulation '{fork_from}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        new_sim = _fork_simulation(fork_from, sim_name)
        new_sim.owner = request.user  # type: ignore[assignment]
        new_sim.map_id = map_obj  # type: ignore[assignment]
        new_sim.visibility = visibility_val
        new_sim.save(update_fields=["owner", "map_id", "visibility"])
    else:
        new_sim = Simulation.objects.create(
            name=sim_name,
            fork_sim_code=None,
            sec_per_step=10,
            maze_name=map_obj.maze_name,
            owner=request.user,
            map_id=map_obj,
            visibility=visibility_val,
        )

    # Create admin membership for the creating user
    SimulationMembership.objects.get_or_create(
        simulation=new_sim,
        user=request.user,
        defaults={"role": SimulationMembership.Role.ADMIN, "status": SimulationMembership.MemberStatus.ACTIVE},
    )

    return Response(
        _sim_summary_from_orm(new_sim),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def simulation_detail(request: Request, sim_id: str) -> Response:
    """GET /api/v1/simulations/:id/ — simulation metadata."""
    try:
        sim = Simulation.objects.get(name=sim_id)
    except Simulation.DoesNotExist:
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(_sim_summary_from_orm(sim))


@api_view(["GET"])
def simulation_state(request: Request, sim_id: str) -> Response:
    """
    GET /api/v1/simulations/:id/state/

    Returns the current world state: agent positions from the latest EnvironmentState row.
    """
    try:
        sim = Simulation.objects.get(name=sim_id)
    except Simulation.DoesNotExist:
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    env = EnvironmentState.objects.filter(simulation=sim).order_by("-step").first()
    return Response(
        {
            "simulation_id": sim_id,
            "step": env.step if env else None,
            "agents": env.agent_positions if env else {},
        }
    )


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
def simulation_agents(request: Request, sim_id: str) -> Response:
    """
    GET /api/v1/simulations/:id/agents/

    Returns all agents with their current position and basic persona info.
    """
    try:
        sim = Simulation.objects.get(name=sim_id)
    except Simulation.DoesNotExist:
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    env = EnvironmentState.objects.filter(simulation=sim).order_by("-step").first()
    positions: dict = env.agent_positions if env else {}
    latest_step: int | None = env.step if env else None

    personas = sim.personas.select_related("scratch").all()
    agents = []
    for p in personas:
        agents.append(
            {
                "id": p.name,
                "name": p.name,
                "first_name": p.first_name,
                "last_name": p.last_name,
                "age": p.age,
                "innate": p.innate,
                "currently": p.currently,
                "location": positions.get(p.name),
            }
        )

    return Response(
        {
            "simulation_id": sim_id,
            "step": latest_step,
            "agents": agents,
        }
    )


@api_view(["GET"])
def simulation_agent_detail(request: Request, sim_id: str, agent_id: str) -> Response:
    """
    GET /api/v1/simulations/:id/agents/:agent_id/

    Returns detailed agent state: persona info, current location, plan, memory summary.
    agent_id is the agent's full name (URL-encoded, spaces as %20 or +).
    """
    try:
        sim = Simulation.objects.get(name=sim_id)
    except Simulation.DoesNotExist:
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        persona = sim.personas.select_related("scratch").get(name=agent_id)
    except Persona.DoesNotExist:
        return Response(
            {"error": f"agent '{agent_id}' not found in simulation '{sim_id}'"},
            status=status.HTTP_404_NOT_FOUND,
        )

    scratch = getattr(persona, "scratch", None)

    env = EnvironmentState.objects.filter(simulation=sim).order_by("-step").first()
    latest_step: int | None = env.step if env else None
    positions: dict = env.agent_positions if env else {}
    position = positions.get(agent_id)

    curr_time_str = scratch.curr_time.isoformat() if scratch and scratch.curr_time else None

    return Response(
        {
            "simulation_id": sim_id,
            "step": latest_step,
            "id": agent_id,
            "name": persona.name,
            "first_name": persona.first_name,
            "last_name": persona.last_name,
            "age": persona.age,
            "innate": persona.innate,
            "learned": persona.learned,
            "currently": persona.currently,
            "lifestyle": persona.lifestyle,
            "living_area": persona.living_area,
            "daily_plan_req": persona.daily_plan_req,
            "curr_time": curr_time_str,
            "vision_r": scratch.vision_r if scratch else None,
            "att_bandwidth": scratch.att_bandwidth if scratch else None,
            "location": position,
        }
    )


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------


def _demo_summary_from_orm(demo: Demo) -> dict:
    """Return summary dict from a Demo ORM object."""
    return {
        "id": demo.name,
        "name": demo.name,
        "fork_sim_code": demo.fork_sim_code,
        "start_date": demo.start_date.isoformat() if demo.start_date else None,
        "curr_time": demo.curr_time.isoformat() if demo.curr_time else None,
        "sec_per_step": demo.sec_per_step,
        "maze_name": demo.maze_name,
        "persona_names": demo.persona_names,
        "step": demo.step,
        "total_steps": demo.total_steps,
    }


# ---------------------------------------------------------------------------
# Demo endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
def demos_list(request: Request) -> Response:
    """GET /api/v1/demos/ — list all available demos."""
    demos = [_demo_summary_from_orm(d) for d in Demo.objects.all()]
    return Response({"demos": demos})


@api_view(["GET"])
def demo_step(request: Request, demo_id: str, step: int) -> Response:
    """
    GET /api/v1/demos/:id/step/:step/

    Returns the world state at a given simulation step from DemoMovement.
    Each agent entry has: movement [x, y], pronunciatio (emoji), description, chat.
    """
    try:
        demo = Demo.objects.get(name=demo_id)
    except Demo.DoesNotExist:
        return Response(
            {"error": f"demo '{demo_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        dm = DemoMovement.objects.get(demo=demo, step=step)
    except DemoMovement.DoesNotExist:
        return Response(
            {"error": f"step {step} not found in demo '{demo_id}'"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(
        {
            "demo_id": demo_id,
            "step": step,
            "sec_per_step": demo.sec_per_step,
            "agents": dm.agent_movements,
        }
    )
