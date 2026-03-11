"""
Optional database persistence bridge for reverie.py.

This module provides functions to write simulation state to the Django ORM
(frontend_server translator models). It is entirely optional: if Django is
not set up or DJANGO_SETTINGS_MODULE is not configured, all calls become
no-ops and a warning is logged once.

Usage from reverie.py (or any non-Django process):
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "frontend_server.settings.development")
    from db_persistence import init_django, get_or_create_simulation, ...
    init_django()  # must be called before any DB functions
"""

from __future__ import annotations

import datetime
import logging
import os
import sys
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Global flag — True once django.setup() has succeeded.
_django_ready: bool = False
# Set to True once we have already warned that Django is unavailable.
_warned_unavailable: bool = False


def init_django() -> bool:
    """
    Call django.setup() so that the ORM is available in a standalone process.

    Returns True on success, False if Django cannot be initialised (e.g.
    DJANGO_SETTINGS_MODULE is not set or the package is not on sys.path).
    """
    global _django_ready, _warned_unavailable

    if _django_ready:
        return True

    settings_module = os.environ.get("DJANGO_SETTINGS_MODULE", "")
    if not settings_module:
        if not _warned_unavailable:
            logger.warning(
                "db_persistence: DJANGO_SETTINGS_MODULE is not set — simulation will not be persisted to the database."
            )
            _warned_unavailable = True
        return False

    # Ensure the frontend_server package root is on sys.path so that
    # Django can import settings and translator models.
    frontend_root = os.path.join(os.path.dirname(__file__), "..", "frontend_server")
    frontend_root = os.path.normpath(frontend_root)
    if frontend_root not in sys.path:
        sys.path.insert(0, frontend_root)

    try:
        import django

        django.setup()
        _django_ready = True
        logger.info("db_persistence: Django ORM initialised (%s)", settings_module)
        return True
    except Exception as exc:
        if not _warned_unavailable:
            logger.warning(
                "db_persistence: Failed to initialise Django — DB persistence disabled. Error: %s",
                exc,
            )
            _warned_unavailable = True
        return False


def _is_ready() -> bool:
    """Return True if Django is ready; log a warning once if not."""
    global _warned_unavailable
    if _django_ready:
        return True
    if not _warned_unavailable:
        logger.warning("db_persistence: Django not initialised — call init_django() first.")
        _warned_unavailable = True
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_or_create_simulation(
    sim_code: str,
    *,
    status: str = "running",
    config: Optional[dict[str, Any]] = None,
) -> Optional[Any]:
    """
    Get or create a Simulation record by name.

    Returns the ORM object, or None if Django is unavailable.
    """
    if not _is_ready():
        return None
    try:
        from translator.models import Simulation

        sim, created = Simulation.objects.get_or_create(
            name=sim_code,
            defaults={
                "status": status,
                "config": config or {},
            },
        )
        if not created and sim.status != status:
            sim.status = status
            sim.save(update_fields=["status", "updated_at"])
        action = "created" if created else "retrieved"
        logger.debug("db_persistence: simulation '%s' %s (pk=%s)", sim_code, action, sim.pk)
        return sim
    except Exception as exc:
        logger.error("db_persistence: get_or_create_simulation failed: %s", exc, exc_info=True)
        return None


def update_simulation_status(sim_obj: Any, status: str) -> None:
    """Update the status field of a Simulation ORM object."""
    if not _is_ready() or sim_obj is None:
        return
    try:
        sim_obj.status = status
        sim_obj.save(update_fields=["status", "updated_at"])
        logger.debug("db_persistence: simulation '%s' status → %s", sim_obj.name, status)
    except Exception as exc:
        logger.error("db_persistence: update_simulation_status failed: %s", exc, exc_info=True)


def upsert_agent(
    sim_obj: Any,
    persona_name: str,
    *,
    personality_traits: str = "",
    current_location: str = "",
    status: str = "active",
) -> Optional[Any]:
    """
    Get-or-create an Agent record for this simulation and persona name.

    Returns the ORM object, or None if Django is unavailable.
    """
    if not _is_ready() or sim_obj is None:
        return None
    try:
        from translator.models import Agent

        agent, _ = Agent.objects.get_or_create(
            simulation=sim_obj,
            name=persona_name,
            defaults={
                "personality_traits": personality_traits,
                "current_location": current_location,
                "status": status,
            },
        )
        # Update mutable fields on every call.
        updated_fields = []
        if agent.current_location != current_location:
            agent.current_location = current_location
            updated_fields.append("current_location")
        if agent.status != status:
            agent.status = status
            updated_fields.append("status")
        if personality_traits and agent.personality_traits != personality_traits:
            agent.personality_traits = personality_traits
            updated_fields.append("personality_traits")
        if updated_fields:
            agent.save(update_fields=updated_fields)
        return agent
    except Exception as exc:
        logger.error("db_persistence: upsert_agent failed for '%s': %s", persona_name, exc, exc_info=True)
        return None


def save_simulation_step(
    sim_obj: Any,
    step_number: int,
    timestamp: datetime.datetime,
    world_state: dict[str, Any],
) -> None:
    """
    Upsert a SimulationStep record.

    Uses update_or_create so that re-running a simulation step from the same
    step number updates the existing record rather than raising an IntegrityError.
    """
    if not _is_ready() or sim_obj is None:
        return
    try:
        from translator.models import SimulationStep

        # Ensure timestamp is timezone-aware (UTC).
        if timestamp.tzinfo is None:
            import datetime as _dt

            timestamp = timestamp.replace(tzinfo=_dt.timezone.utc)

        SimulationStep.objects.update_or_create(
            simulation=sim_obj,
            step_number=step_number,
            defaults={
                "timestamp": timestamp,
                "world_state": world_state,
            },
        )
        logger.debug("db_persistence: saved step %d for '%s'", step_number, sim_obj.name)
    except Exception as exc:
        logger.error("db_persistence: save_simulation_step failed: %s", exc, exc_info=True)


def save_agent_memory(
    agent_obj: Any,
    memory_type: str,
    content: str,
    importance_score: float = 0.0,
) -> None:
    """
    Append an AgentMemory record.  No deduplication — every call creates a new row.
    (Use the import_simulation management command for bulk, idempotent imports.)
    """
    if not _is_ready() or agent_obj is None:
        return
    try:
        from translator.models import AgentMemory

        AgentMemory.objects.create(
            agent=agent_obj,
            memory_type=memory_type,
            content=content,
            importance_score=importance_score,
        )
    except Exception as exc:
        logger.error("db_persistence: save_agent_memory failed: %s", exc, exc_info=True)


def save_conversation(
    sim_obj: Any,
    agent_objs: list[Any],
    started_at: datetime.datetime,
    transcript: list[list[str]],
) -> None:
    """
    Save a Conversation record with participants and transcript.
    """
    if not _is_ready() or sim_obj is None:
        return
    try:
        from translator.models import Conversation

        if started_at.tzinfo is None:
            import datetime as _dt

            started_at = started_at.replace(tzinfo=_dt.timezone.utc)

        convo = Conversation.objects.create(
            simulation=sim_obj,
            started_at=started_at,
            transcript=transcript,
        )
        if agent_objs:
            convo.participants.set(agent_objs)
        logger.debug(
            "db_persistence: saved conversation (pk=%s) for '%s'",
            convo.pk,
            sim_obj.name,
        )
    except Exception as exc:
        logger.error("db_persistence: save_conversation failed: %s", exc, exc_info=True)
