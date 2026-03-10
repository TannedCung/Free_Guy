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

import json
import os
import shutil
import string
import random

from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response


STORAGE_DIR = os.path.join(settings.BASE_DIR, "storage")
COMPRESSED_STORAGE_DIR = os.path.join(settings.BASE_DIR, "compressed_storage")


def _sim_exists(sim_code: str) -> bool:
    return os.path.isdir(os.path.join(STORAGE_DIR, sim_code))


def _load_meta(sim_code: str) -> dict:
    """Return the reverie/meta.json for a simulation, or {} if missing."""
    meta_path = os.path.join(STORAGE_DIR, sim_code, "reverie", "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f)
    return {}


def _latest_env_step(sim_code: str) -> int | None:
    """Return the highest step number found in environment/, or None."""
    env_dir = os.path.join(STORAGE_DIR, sim_code, "environment")
    if not os.path.isdir(env_dir):
        return None
    steps = []
    for fname in os.listdir(env_dir):
        if fname.endswith(".json"):
            try:
                steps.append(int(fname.replace(".json", "")))
            except ValueError:
                pass
    return max(steps) if steps else None


def _simulation_summary(sim_code: str) -> dict:
    meta = _load_meta(sim_code)
    return {
        "id": sim_code,
        "name": sim_code,
        "fork_sim_code": meta.get("fork_sim_code"),
        "start_date": meta.get("start_date"),
        "curr_time": meta.get("curr_time"),
        "sec_per_step": meta.get("sec_per_step"),
        "maze_name": meta.get("maze_name"),
        "persona_names": meta.get("persona_names", []),
        "step": meta.get("step", 0),
    }


@api_view(["GET", "POST"])
def simulations_list(request: Request) -> Response:
    """
    GET  - list all available simulations.
    POST - create a new simulation or fork from an existing one.
    """
    if request.method == "GET":
        if not os.path.isdir(STORAGE_DIR):
            return Response({"simulations": []})
        sims = []
        for name in sorted(os.listdir(STORAGE_DIR)):
            if os.path.isdir(os.path.join(STORAGE_DIR, name)):
                sims.append(_simulation_summary(name))
        return Response({"simulations": sims})

    # POST — create or fork
    sim_name: str = request.data.get("name", "").strip()
    fork_from: str = request.data.get("fork_from", "").strip()

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

    new_sim_code = sim_name
    new_sim_dir = os.path.join(STORAGE_DIR, new_sim_code)

    if os.path.exists(new_sim_dir):
        return Response(
            {"error": f"simulation '{new_sim_code}' already exists"},
            status=status.HTTP_409_CONFLICT,
        )

    if fork_from:
        if not _sim_exists(fork_from):
            return Response(
                {"error": f"fork_from simulation '{fork_from}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        shutil.copytree(os.path.join(STORAGE_DIR, fork_from), new_sim_dir)
        # Update meta to record the fork
        meta = _load_meta(new_sim_code)
        meta["fork_sim_code"] = fork_from
        meta_path = os.path.join(new_sim_dir, "reverie", "meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)
    else:
        # Minimal scaffold for a brand-new simulation
        os.makedirs(os.path.join(new_sim_dir, "reverie"))
        os.makedirs(os.path.join(new_sim_dir, "environment"))
        os.makedirs(os.path.join(new_sim_dir, "movement"))
        os.makedirs(os.path.join(new_sim_dir, "personas"))
        meta = {
            "fork_sim_code": None,
            "start_date": None,
            "curr_time": None,
            "sec_per_step": 10,
            "maze_name": "the_ville",
            "persona_names": [],
            "step": 0,
        }
        meta_path = os.path.join(new_sim_dir, "reverie", "meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

    return Response(
        _simulation_summary(new_sim_code),
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def simulation_detail(request: Request, sim_id: str) -> Response:
    """GET /api/v1/simulations/:id/ — simulation metadata."""
    if not _sim_exists(sim_id):
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )
    return Response(_simulation_summary(sim_id))


@api_view(["GET"])
def simulation_state(request: Request, sim_id: str) -> Response:
    """
    GET /api/v1/simulations/:id/state/

    Returns the current world state: agent positions from the latest
    environment/{step}.json file.
    """
    if not _sim_exists(sim_id):
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    latest_step = _latest_env_step(sim_id)
    if latest_step is None:
        return Response(
            {
                "simulation_id": sim_id,
                "step": None,
                "agents": {},
            }
        )

    env_path = os.path.join(STORAGE_DIR, sim_id, "environment", f"{latest_step}.json")
    with open(env_path) as f:
        env_data = json.load(f)

    return Response(
        {
            "simulation_id": sim_id,
            "step": latest_step,
            "agents": env_data,
        }
    )


# ---------------------------------------------------------------------------
# Agent helpers
# ---------------------------------------------------------------------------


def _load_scratch(sim_code: str, agent_name: str) -> dict:
    """Return scratch.json for an agent, or {} if missing."""
    scratch_path = os.path.join(
        STORAGE_DIR, sim_code, "personas", agent_name, "bootstrap_memory", "scratch.json"
    )
    if os.path.exists(scratch_path):
        with open(scratch_path) as f:
            return json.load(f)
    return {}


def _agent_summary(agent_name: str, scratch: dict, position: dict | None) -> dict:
    """Return a summary dict for an agent."""
    return {
        "id": agent_name,
        "name": agent_name,
        "first_name": scratch.get("first_name"),
        "last_name": scratch.get("last_name"),
        "age": scratch.get("age"),
        "innate": scratch.get("innate"),
        "currently": scratch.get("currently"),
        "location": position,
    }


# ---------------------------------------------------------------------------
# Agent endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
def simulation_agents(request: Request, sim_id: str) -> Response:
    """
    GET /api/v1/simulations/:id/agents/

    Returns all agents with their current position and basic persona info.
    """
    if not _sim_exists(sim_id):
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    meta = _load_meta(sim_id)
    persona_names: list[str] = meta.get("persona_names", [])

    # Load latest environment state for positions
    latest_step = _latest_env_step(sim_id)
    positions: dict = {}
    if latest_step is not None:
        env_path = os.path.join(STORAGE_DIR, sim_id, "environment", f"{latest_step}.json")
        with open(env_path) as f:
            positions = json.load(f)

    agents = []
    for name in persona_names:
        scratch = _load_scratch(sim_id, name)
        agents.append(_agent_summary(name, scratch, positions.get(name)))

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
    if not _sim_exists(sim_id):
        return Response(
            {"error": f"simulation '{sim_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    meta = _load_meta(sim_id)
    persona_names: list[str] = meta.get("persona_names", [])

    if agent_id not in persona_names:
        return Response(
            {"error": f"agent '{agent_id}' not found in simulation '{sim_id}'"},
            status=status.HTTP_404_NOT_FOUND,
        )

    scratch = _load_scratch(sim_id, agent_id)

    # Current position from latest env step
    latest_step = _latest_env_step(sim_id)
    position = None
    if latest_step is not None:
        env_path = os.path.join(STORAGE_DIR, sim_id, "environment", f"{latest_step}.json")
        with open(env_path) as f:
            env_data = json.load(f)
        position = env_data.get(agent_id)

    return Response(
        {
            "simulation_id": sim_id,
            "step": latest_step,
            "id": agent_id,
            "name": scratch.get("name", agent_id),
            "first_name": scratch.get("first_name"),
            "last_name": scratch.get("last_name"),
            "age": scratch.get("age"),
            "innate": scratch.get("innate"),
            "learned": scratch.get("learned"),
            "currently": scratch.get("currently"),
            "lifestyle": scratch.get("lifestyle"),
            "living_area": scratch.get("living_area"),
            "daily_plan_req": scratch.get("daily_plan_req"),
            "curr_time": scratch.get("curr_time"),
            "vision_r": scratch.get("vision_r"),
            "att_bandwidth": scratch.get("att_bandwidth"),
            "location": position,
        }
    )


# ---------------------------------------------------------------------------
# Demo helpers
# ---------------------------------------------------------------------------


def _demo_exists(demo_code: str) -> bool:
    return os.path.isdir(os.path.join(COMPRESSED_STORAGE_DIR, demo_code))


def _load_demo_meta(demo_code: str) -> dict:
    """Return meta.json for a demo, or {} if missing."""
    meta_path = os.path.join(COMPRESSED_STORAGE_DIR, demo_code, "meta.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f)
    return {}


def _demo_summary(demo_code: str) -> dict:
    meta = _load_demo_meta(demo_code)
    # Count total steps from master_movement.json if present
    total_steps: int | None = None
    mvmt_path = os.path.join(COMPRESSED_STORAGE_DIR, demo_code, "master_movement.json")
    if os.path.exists(mvmt_path):
        with open(mvmt_path) as f:
            movement = json.load(f)
        total_steps = len(movement)
    return {
        "id": demo_code,
        "name": demo_code,
        "fork_sim_code": meta.get("fork_sim_code"),
        "start_date": meta.get("start_date"),
        "curr_time": meta.get("curr_time"),
        "sec_per_step": meta.get("sec_per_step"),
        "maze_name": meta.get("maze_name"),
        "persona_names": meta.get("persona_names", []),
        "step": meta.get("step", 0),
        "total_steps": total_steps,
    }


# ---------------------------------------------------------------------------
# Demo endpoints
# ---------------------------------------------------------------------------


@api_view(["GET"])
def demos_list(request: Request) -> Response:
    """GET /api/v1/demos/ — list all available demos."""
    if not os.path.isdir(COMPRESSED_STORAGE_DIR):
        return Response({"demos": []})
    demos = []
    for name in sorted(os.listdir(COMPRESSED_STORAGE_DIR)):
        if os.path.isdir(os.path.join(COMPRESSED_STORAGE_DIR, name)):
            demos.append(_demo_summary(name))
    return Response({"demos": demos})


@api_view(["GET"])
def demo_step(request: Request, demo_id: str, step: int) -> Response:
    """
    GET /api/v1/demos/:id/step/:step/

    Returns the world state at a given simulation step from master_movement.json.
    Each agent entry has: movement [x, y], pronunciatio (emoji), description, chat.
    """
    if not _demo_exists(demo_id):
        return Response(
            {"error": f"demo '{demo_id}' not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    mvmt_path = os.path.join(COMPRESSED_STORAGE_DIR, demo_id, "master_movement.json")
    if not os.path.exists(mvmt_path):
        return Response(
            {"error": f"demo '{demo_id}' has no movement data"},
            status=status.HTTP_404_NOT_FOUND,
        )

    with open(mvmt_path) as f:
        movement = json.load(f)

    step_key = str(step)
    if step_key not in movement:
        return Response(
            {"error": f"step {step} not found in demo '{demo_id}'"},
            status=status.HTTP_404_NOT_FOUND,
        )

    meta = _load_demo_meta(demo_id)
    return Response(
        {
            "demo_id": demo_id,
            "step": step,
            "sec_per_step": meta.get("sec_per_step"),
            "agents": movement[step_key],
        }
    )
