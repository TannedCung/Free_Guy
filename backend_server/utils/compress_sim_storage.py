"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: compress_sim_storage.py
Description: Compresses a simulation for replay demos using PostgreSQL.
  Queries Simulation, Persona, and MovementRecord from DB to build a
  deduplicated movement timeline, then writes Demo + DemoMovement rows.
"""

from __future__ import annotations


def compress(sim_code: str) -> None:
    """Compress a simulation into Demo + DemoMovement DB rows.

    The caller is responsible for ensuring Django is initialised before
    calling this function (e.g. via db_persistence.init_django()).
    """
    from translator.models import Demo, DemoMovement, MovementRecord, Simulation

    sim = Simulation.objects.get(name=sim_code)
    persona_names: list[str] = list(sim.personas.values_list("name", flat=True))

    # Stream movement records in step order
    movement_records = MovementRecord.objects.filter(simulation=sim).order_by("step")
    total_steps = movement_records.count()

    persona_last_move: dict[str, dict] = {}
    demo_movement_data: list[tuple[int, dict]] = []

    for record in movement_records:
        step_data: dict[str, dict] = {}
        p_moves: dict = record.persona_movements  # {persona_name: {movement, pronunciatio, ...}}

        for p in persona_names:
            if p not in p_moves:
                continue
            p_info: dict = p_moves[p]
            has_changed = (
                p not in persona_last_move
                or p_info.get("movement") != persona_last_move[p].get("movement")
                or p_info.get("pronunciatio") != persona_last_move[p].get("pronunciatio")
                or p_info.get("description") != persona_last_move[p].get("description")
                or p_info.get("chat") != persona_last_move[p].get("chat")
            )
            if has_changed:
                entry: dict = {
                    "movement": p_info.get("movement"),
                    "pronunciatio": p_info.get("pronunciatio"),
                    "description": p_info.get("description"),
                    "chat": p_info.get("chat"),
                }
                persona_last_move[p] = entry
                step_data[p] = entry

        if step_data:
            demo_movement_data.append((record.step, step_data))

    # Upsert Demo row
    demo, _ = Demo.objects.update_or_create(
        name=sim_code,
        defaults={
            "fork_sim_code": sim.fork_sim_code or sim_code,
            "start_date": sim.start_date,
            "curr_time": sim.curr_time,
            "sec_per_step": sim.sec_per_step,
            "maze_name": sim.maze_name,
            "persona_names": persona_names,
            "step": sim.step,
            "total_steps": total_steps,
        },
    )

    # Replace DemoMovement rows (idempotent: delete then bulk-create)
    DemoMovement.objects.filter(demo=demo).delete()
    DemoMovement.objects.bulk_create(
        [DemoMovement(demo=demo, step=s, agent_movements=mv) for s, mv in demo_movement_data],
        batch_size=500,
    )

    print(f"Compressed {sim_code}: {total_steps} total steps → {len(demo_movement_data)} demo movements stored in DB")


if __name__ == "__main__":
    import os
    import sys

    # Ensure the frontend_server root is importable so Django settings & models load.
    _here = os.path.dirname(os.path.abspath(__file__))
    _frontend_root = os.path.normpath(os.path.join(_here, "..", "..", "frontend_server"))
    if _frontend_root not in sys.path:
        sys.path.insert(0, _frontend_root)

    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        os.environ["DJANGO_SETTINGS_MODULE"] = "frontend_server.settings.development"

    import django

    django.setup()

    compress("July1_the_ville_isabella_maria_klaus-step-3-9")
