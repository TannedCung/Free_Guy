"""Backend simulation loop runner.

Manages one daemon thread per active simulation that drives the
perceive → retrieve → plan → reflect → execute cycle, replacing the
frontend-driven step loop.

Public API
----------
start(sim_id)            — spawn a runner thread (no-op if already alive)
resume_all_running()     — called once from AppConfig.ready(); resumes every
                           Simulation with status=RUNNING after a short delay
                           so Django/DB is fully initialised first.
"""

import logging
import os
import sys
import threading
import time

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_active: dict[str, threading.Thread] = {}
_sim_locks: dict[str, threading.Lock] = {}  # per-simulation step-execution lock
_startup_done = False  # guard against double AppConfig.ready() calls

STAGES = ["run_perceive", "run_retrieve", "run_plan", "run_reflect", "run_execute"]


def _ensure_backend_on_path() -> None:
    bd = os.path.join(
        os.path.dirname(  # frontend_server/
            os.path.dirname(  # Free_Guy/
                os.path.dirname(os.path.abspath(__file__))
            )
        ),
        "backend_server",
    )
    if bd not in sys.path:
        sys.path.insert(0, bd)


def _write_env_state(sim, step: int, movements: dict) -> None:
    """Write EnvironmentState for `step` using the positions from `movements`.

    run_execute returns {"persona": {name: {"movement": [x, y], ...}, ...}}.
    The movement tile is WHERE the agent will be at the start of `step`, so
    we persist it so the next run_execute call can read the correct positions
    instead of falling back to the stale scratch.curr_tile.
    """
    from translator.models import EnvironmentState

    positions: dict[str, dict] = {}
    for persona_name, mv in movements.get("persona", {}).items():
        tile = mv.get("movement")
        if tile:
            positions[persona_name] = {"x": int(tile[0]), "y": int(tile[1])}

    if not positions:
        return

    EnvironmentState.objects.update_or_create(
        simulation=sim,
        step=step,
        defaults={"agent_positions": positions},
    )


def _loop(sim_id: str) -> None:
    """Run the simulation step loop until the simulation is no longer RUNNING."""
    from django import db as django_db

    _ensure_backend_on_path()

    try:
        from reverie import ReverieServer  # noqa: PLC0415
    except Exception as exc:
        logger.error("[runner:%s] Cannot import ReverieServer: %s", sim_id, exc)
        with _lock:
            _active.pop(sim_id, None)
        return

    logger.info("[runner:%s] Loop started", sim_id)

    while True:
        django_db.close_old_connections()

        from translator.models import Simulation

        try:
            sim = Simulation.objects.get(name=sim_id)
        except Simulation.DoesNotExist:
            logger.warning("[runner:%s] Simulation no longer exists — stopping", sim_id)
            break

        if sim.status != Simulation.Status.RUNNING:
            logger.info("[runner:%s] Status is %s — stopping loop", sim_id, sim.status)
            break

        # Acquire the per-simulation lock so concurrent threads (e.g. from a
        # double ready() call) don't interleave stages of the same step.
        sim_lock = _sim_locks.get(sim_id) or threading.Lock()
        with sim_lock:
            step_aborted = False
            for stage_fn_name in STAGES:
                django_db.close_old_connections()

                # Re-read status before every stage so pause/stop is respected.
                try:
                    sim.refresh_from_db(fields=["status"])
                except Exception as exc:
                    logger.error("[runner:%s] refresh_from_db failed: %s", sim_id, exc)
                    step_aborted = True
                    break

                if sim.status != Simulation.Status.RUNNING:
                    logger.info("[runner:%s] Paused/stopped mid-step at %s", sim_id, stage_fn_name)
                    step_aborted = True
                    break

                try:
                    result = getattr(ReverieServer, stage_fn_name)(sim_id)

                    if stage_fn_name == "run_execute":
                        # After execute, sim.step was incremented.  Write agent
                        # positions as EnvironmentState for the new step so the
                        # next run_execute knows where each agent currently stands.
                        sim.refresh_from_db(fields=["step"])
                        _write_env_state(sim, sim.step, result.get("movements", {}))

                except RuntimeError as exc:
                    logger.error("[runner:%s] %s raised RuntimeError: %s", sim_id, stage_fn_name, exc)
                    step_aborted = True
                    time.sleep(5)
                    break
                except Exception:
                    logger.exception("[runner:%s] %s raised unexpected error", sim_id, stage_fn_name)
                    step_aborted = True
                    time.sleep(10)
                    break

        if step_aborted:
            # Check if still running; if not, exit the outer while loop.
            django_db.close_old_connections()
            try:
                sim.refresh_from_db(fields=["status"])
                if sim.status != Simulation.Status.RUNNING:
                    break
            except Exception:
                break

    with _lock:
        _active.pop(sim_id, None)
    logger.info("[runner:%s] Loop ended", sim_id)


def start(sim_id: str) -> bool:
    """Spawn a runner thread for sim_id if one is not already alive.

    Returns True if a new thread was started, False if one was already running.
    """
    with _lock:
        existing = _active.get(sim_id)
        if existing and existing.is_alive():
            logger.debug("[runner:%s] Thread already running", sim_id)
            return False
        if sim_id not in _sim_locks:
            _sim_locks[sim_id] = threading.Lock()
        t = threading.Thread(
            target=_loop,
            args=(sim_id,),
            daemon=True,
            name=f"sim-runner-{sim_id}",
        )
        _active[sim_id] = t
        t.start()
        logger.info("[runner:%s] New thread spawned", sim_id)
        return True


def resume_all_running() -> None:
    """Find all RUNNING simulations and start their loops.

    Runs in a short-delay daemon thread so it doesn't block AppConfig.ready().
    The 5-second sleep gives Django, the ORM, and the DB connection pool time
    to fully initialise before we hit the database.

    Safe to call multiple times — only the first call per process does anything.
    """
    global _startup_done
    with _lock:
        if _startup_done:
            return
        _startup_done = True

    def _deferred() -> None:
        time.sleep(5)
        from django import db as django_db

        django_db.close_old_connections()
        from translator.models import Simulation

        try:
            running = list(Simulation.objects.filter(status=Simulation.Status.RUNNING).values_list("name", flat=True))
        except Exception as exc:
            logger.error("[runner] Failed to query running simulations on startup: %s", exc)
            return

        if running:
            logger.info("[runner] Auto-resuming %d simulation(s) after restart: %s", len(running), running)
        for sim_id in running:
            start(sim_id)

    threading.Thread(target=_deferred, daemon=True, name="sim-runner-startup").start()
