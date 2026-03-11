"""Management command to export simulation data from the database back to JSON files.

This provides backwards compatibility for tooling that reads the flat-file
storage format produced by reverie.py.

Usage:
    python manage.py export_simulation <sim_name> [--output-dir /path/to/storage]
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from translator.models import Agent, Simulation, SimulationStep

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Export simulation data from the database to JSON files (reverie storage format)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "sim_name",
            type=str,
            help="Name of the simulation to export (matches Simulation.name in the database).",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="storage",
            help="Directory where the simulation folder will be written (default: storage/).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sim_name: str = options["sim_name"]
        output_dir = Path(options["output_dir"]).resolve()

        # --- Fetch simulation ---
        try:
            simulation = Simulation.objects.get(name=sim_name)
        except Simulation.DoesNotExist:
            raise CommandError(f"Simulation '{sim_name}' not found in the database.")
        except Simulation.MultipleObjectsReturned:
            # If duplicates exist, use the most recently created one.
            simulation = Simulation.objects.filter(name=sim_name).order_by("-created_at").first()  # type: ignore[assignment]

        self.stdout.write(f"Exporting simulation: {simulation.name} (pk={simulation.pk})")

        sim_dir = output_dir / simulation.name
        sim_dir.mkdir(parents=True, exist_ok=True)

        # --- Export reverie meta.json ---
        config: dict[str, Any] = simulation.config or {}
        meta: dict[str, Any] = {
            "fork_sim_code": config.get("fork_sim_code", simulation.name),
            "start_date": config.get("start_time", "June 25, 2022").split(",")[0].strip()
            if "," in config.get("start_time", "")
            else config.get("start_time", "June 25, 2022"),
            "curr_time": config.get("start_time", "June 25, 2022, 00:00:00"),
            "sec_per_step": config.get("sec_per_step", 10),
            "maze_name": config.get("maze_name", "the_ville"),
            "persona_names": list(simulation.agents.values_list("name", flat=True)),
            "step": SimulationStep.objects.filter(simulation=simulation).count(),
        }
        reverie_dir = sim_dir / "reverie"
        reverie_dir.mkdir(exist_ok=True)
        _write_json(reverie_dir / "meta.json", meta)
        self.stdout.write(f"  Wrote reverie/meta.json (step={meta['step']})")

        # --- Export environment files (one per step) ---
        steps_qs = SimulationStep.objects.filter(simulation=simulation).order_by("step_number")
        step_count = steps_qs.count()
        self.stdout.write(f"  Exporting {step_count} simulation steps …")

        env_dir = sim_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        movement_dir = sim_dir / "movement"
        movement_dir.mkdir(exist_ok=True)

        for step_obj in steps_qs:
            world_state: dict[str, Any] = step_obj.world_state or {}
            step_num = step_obj.step_number

            # movement/<step>.json — raw world_state (movements dict)
            _write_json(movement_dir / f"{step_num}.json", world_state)

            # environment/<step>.json — agent positions extracted from world_state
            env: dict[str, Any] = {}
            personas = world_state.get("persona", {})
            for persona_name, persona_data in personas.items():
                movement = persona_data.get("movement", [0, 0])
                env[persona_name] = {
                    "x": movement[0] if isinstance(movement, list) and len(movement) > 0 else 0,
                    "y": movement[1] if isinstance(movement, list) and len(movement) > 1 else 0,
                }
            _write_json(env_dir / f"{step_num}.json", env)

        self.stdout.write(f"  Wrote {step_count} movement and environment files.")

        # --- Export persona bootstrap memory (from Agent records) ---
        agents: list[Agent] = list(simulation.agents.all())
        personas_dir = sim_dir / "personas"
        personas_dir.mkdir(exist_ok=True)

        for agent in agents:
            persona_dir = personas_dir / agent.name / "bootstrap_memory"
            persona_dir.mkdir(parents=True, exist_ok=True)

            # scratch.json — minimal scratch state from DB fields
            scratch: dict[str, Any] = {
                "name": agent.name,
                "curr_time": None,
                "curr_tile": None,
                "daily_plan_req": None,
                "innate": agent.personality_traits,
                "learned": "",
                "currently": "",
                "lifestyle": "",
                "living_area": agent.current_location,
                "act_address": agent.current_location,
                "act_start_time": None,
                "act_duration": None,
                "act_description": None,
                "act_pronunciatio": None,
                "act_event": [None, None, None],
                "act_obj_description": None,
                "act_obj_pronunciatio": None,
                "act_obj_event": [None, None, None],
                "chatting_with": None,
                "chat": None,
                "chatting_with_buffer": {},
                "chatting_end_time": None,
                "act_path_set": False,
                "planned_path": [],
                "daily_req": [],
                "f_daily_schedule": [],
                "f_daily_schedule_hourly_org": [],
                "vision_r": 4,
                "att_bandwidth": 3,
                "retention": 5,
                "concept_forget": 100,
                "daily_reflection_time": 60,
                "daily_reflection_size": 5,
                "overlap_reflect_th": 4,
                "kw_strg_event_reflect_th": 10,
                "kw_strg_thought_reflect_th": 9,
                "recency_w": 1,
                "relevance_w": 1,
                "importance_w": 1,
                "recency_decay": 0.99,
                "importance_trigger_max": 150,
                "importance_trigger_curr": 150,
                "importance_ele_n": 0,
                "thought_count": 5,
            }
            _write_json(persona_dir / "scratch.json", scratch)

            # associative_memory/ — memory nodes from AgentMemory
            am_dir = persona_dir / "associative_memory"
            am_dir.mkdir(exist_ok=True)

            memories = list(agent.memories.order_by("created_at"))
            nodes: dict[str, Any] = {}
            kw_strength: dict[str, Any] = {"event": {}, "thought": {}}
            seq_event: list[str] = []
            seq_thought: list[str] = []
            seq_chat: list[str] = []

            for idx, mem in enumerate(memories):
                node_id = f"node_{idx}"
                created_str = mem.created_at.strftime("%Y-%m-%d %H:%M:%S")
                nodes[node_id] = {
                    "node_id": node_id,
                    "node_count": idx,
                    "type_count": idx,
                    "type": mem.memory_type,
                    "depth": 1,
                    "created": created_str,
                    "expiration": None,
                    "last_accessed": created_str,
                    "subject": agent.name,
                    "predicate": "is",
                    "object": mem.content,
                    "description": mem.content,
                    "embedding_key": node_id,
                    "poignancy": int(mem.importance_score),
                    "keywords": [],
                    "filling": [],
                }
                if mem.memory_type == "event":
                    seq_event.append(node_id)
                elif mem.memory_type == "thought":
                    seq_thought.append(node_id)
                elif mem.memory_type == "chat":
                    seq_chat.append(node_id)

            _write_json(am_dir / "nodes.json", nodes)
            _write_json(am_dir / "kw_strength.json", kw_strength)
            _write_json(am_dir / "embeddings.json", {})

            # seq files
            for seq_name, seq_list in [("seq_event", seq_event), ("seq_thought", seq_thought), ("seq_chat", seq_chat)]:
                (am_dir / f"{seq_name}.json").write_text(json.dumps(seq_list, indent=2))

            # spatial_memory.json — empty tree (not stored in DB by current models)
            _write_json(persona_dir / "spatial_memory.json", {})

            self.stdout.write(f"  Exported persona: {agent.name} ({len(memories)} memories)")

        self.stdout.write(self.style.SUCCESS(f"Export complete → {sim_dir}"))


def _write_json(path: Path, data: Any) -> None:
    """Write data as indented JSON to path."""
    path.write_text(json.dumps(data, indent=2, default=str))
