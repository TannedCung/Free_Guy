"""Management command to export simulation data from the database back to JSON files.

Produces the original reverie flat-file storage layout so that legacy tooling
(or the import_simulation command) can round-trip data.

Usage:
    python manage.py export_simulation <sim_name> [--output-dir /path/to/storage]
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Any

import qdrant_utils as qu
from django.core.management.base import BaseCommand, CommandError
from translator.models import (
    ConceptNode,
    EnvironmentState,
    KeywordStrength,
    MovementRecord,
    Persona,
    PersonaScratch,
    Simulation,
    SpatialMemory,
)

logger = logging.getLogger(__name__)

_DEFAULT_OUTPUT = Path(__file__).resolve().parents[3] / "storage"


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
            default=str(_DEFAULT_OUTPUT),
            help=f"Directory where the simulation folder will be written (default: {_DEFAULT_OUTPUT}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sim_name: str = options["sim_name"]
        output_dir = Path(options["output_dir"]).resolve()

        try:
            simulation = Simulation.objects.get(name=sim_name)
        except Simulation.DoesNotExist:
            raise CommandError(f"Simulation '{sim_name}' not found in the database.")

        self.stdout.write(f"Exporting simulation: {simulation.name} (pk={simulation.pk})")

        sim_dir = output_dir / simulation.name
        sim_dir.mkdir(parents=True, exist_ok=True)

        # ── reverie/meta.json ─────────────────────────────────────────────────
        persona_names = list(simulation.personas.values_list("name", flat=True))
        meta: dict[str, Any] = {
            "fork_sim_code": simulation.fork_sim_code or simulation.name,
            "start_date": simulation.start_date.strftime("%B %d, %Y") if simulation.start_date else "",
            "curr_time": simulation.curr_time.strftime("%B %d, %Y, %H:%M:%S") if simulation.curr_time else "",
            "sec_per_step": simulation.sec_per_step,
            "maze_name": simulation.maze_name,
            "persona_names": persona_names,
            "step": simulation.step,
        }
        reverie_dir = sim_dir / "reverie"
        reverie_dir.mkdir(exist_ok=True)
        _write_json(reverie_dir / "meta.json", meta)
        self.stdout.write(f"  Wrote reverie/meta.json (step={meta['step']})")

        # ── environment/*.json ────────────────────────────────────────────────
        env_dir = sim_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        env_qs = EnvironmentState.objects.filter(simulation=simulation).order_by("step")
        env_count = env_qs.count()
        for env_state in env_qs:
            _write_json(env_dir / f"{env_state.step}.json", env_state.agent_positions)
        self.stdout.write(f"  Wrote {env_count} environment files.")

        # ── movement/*.json ───────────────────────────────────────────────────
        movement_dir = sim_dir / "movement"
        movement_dir.mkdir(exist_ok=True)
        mov_qs = MovementRecord.objects.filter(simulation=simulation).order_by("step")
        mov_count = mov_qs.count()
        for record in mov_qs:
            curr_time_str = record.sim_curr_time.strftime("%B %d, %Y, %H:%M:%S") if record.sim_curr_time else ""
            movement_data: dict[str, Any] = {
                "persona": record.persona_movements,
                "meta": {"curr_time": curr_time_str},
            }
            _write_json(movement_dir / f"{record.step}.json", movement_data)
        self.stdout.write(f"  Wrote {mov_count} movement files.")

        # ── personas/*/bootstrap_memory/* ─────────────────────────────────────
        personas_dir = sim_dir / "personas"
        personas_dir.mkdir(exist_ok=True)

        personas = list(simulation.personas.all())
        for persona in personas:
            self._export_persona(persona, personas_dir)

        self.stdout.write(self.style.SUCCESS(f"Export complete → {sim_dir}"))

    def _export_persona(self, persona: Persona, personas_dir: Path) -> None:
        mem_dir = personas_dir / persona.name / "bootstrap_memory"
        mem_dir.mkdir(parents=True, exist_ok=True)
        am_dir = mem_dir / "associative_memory"
        am_dir.mkdir(exist_ok=True)

        # scratch.json
        scratch_data = _build_scratch(persona)
        _write_json(mem_dir / "scratch.json", scratch_data)

        # spatial_memory.json
        try:
            spatial = persona.spatial_memory
            tree = spatial.tree
        except SpatialMemory.DoesNotExist:
            tree = {}
        _write_json(mem_dir / "spatial_memory.json", tree)

        # associative_memory/nodes.json
        nodes_qs = ConceptNode.objects.filter(persona=persona).order_by("node_id")
        nodes: dict[str, Any] = {}
        seq_event: list[str] = []
        seq_thought: list[str] = []
        seq_chat: list[str] = []
        for node in nodes_qs:
            node_key = f"node_{node.node_id}"
            nodes[node_key] = {
                "node_id": node_key,
                "node_count": node.node_count,
                "type_count": node.type_count,
                "type": node.node_type,
                "depth": node.depth,
                "created": node.created.strftime("%Y-%m-%d %H:%M:%S") if node.created else None,
                "expiration": node.expiration.strftime("%Y-%m-%d %H:%M:%S") if node.expiration else None,
                "last_accessed": node.last_accessed.strftime("%Y-%m-%d %H:%M:%S") if node.last_accessed else None,
                "subject": node.subject,
                "predicate": node.predicate,
                "object": node.object,
                "description": node.description,
                "embedding_key": node.embedding_key,
                "poignancy": node.poignancy,
                "keywords": node.keywords,
                "filling": node.filling,
            }
            if node.node_type == "event":
                seq_event.append(node_key)
            elif node.node_type == "thought":
                seq_thought.append(node_key)
            elif node.node_type == "chat":
                seq_chat.append(node_key)
        _write_json(am_dir / "nodes.json", nodes)

        for seq_name, seq_list in [
            ("seq_event", seq_event),
            ("seq_thought", seq_thought),
            ("seq_chat", seq_chat),
        ]:
            _write_json(am_dir / f"{seq_name}.json", seq_list)

        # associative_memory/kw_strength.json
        kw_event: dict[str, int] = {}
        kw_thought: dict[str, int] = {}
        for kw in KeywordStrength.objects.filter(persona=persona):
            if kw.strength_type == "event":
                kw_event[kw.keyword] = kw.strength
            else:
                kw_thought[kw.keyword] = kw.strength
        _write_json(
            am_dir / "kw_strength.json",
            {"kw_strength_event": kw_event, "kw_strength_thought": kw_thought},
        )

        # associative_memory/embeddings.json
        try:
            embeddings = qu.get_all_persona_embeddings(persona.pk)
        except Exception as exc:
            warnings.warn(f"Qdrant retrieval failed for {persona.name}: {exc}", stacklevel=2)
            embeddings = {}
        _write_json(am_dir / "embeddings.json", embeddings)

        n_nodes = len(nodes)
        n_emb = len(embeddings)
        self.stdout.write(f"  Exported persona: {persona.name} ({n_nodes} nodes, {n_emb} embeddings)")


def _build_scratch(persona: Persona) -> dict[str, Any]:
    """Build scratch.json dict from Persona + PersonaScratch rows."""
    base: dict[str, Any] = {
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
    }
    try:
        s: PersonaScratch = persona.scratch
    except PersonaScratch.DoesNotExist:
        return base

    base.update(
        {
            "vision_r": s.vision_r,
            "att_bandwidth": s.att_bandwidth,
            "retention": s.retention,
            "curr_time": s.curr_time.strftime("%B %d, %Y, %H:%M:%S") if s.curr_time else None,
            "curr_tile": s.curr_tile,
            "concept_forget": s.concept_forget,
            "daily_reflection_time": s.daily_reflection_time,
            "daily_reflection_size": s.daily_reflection_size,
            "overlap_reflect_th": s.overlap_reflect_th,
            "kw_strg_event_reflect_th": s.kw_strg_event_reflect_th,
            "kw_strg_thought_reflect_th": s.kw_strg_thought_reflect_th,
            "recency_w": s.recency_w,
            "relevance_w": s.relevance_w,
            "importance_w": s.importance_w,
            "recency_decay": s.recency_decay,
            "importance_trigger_max": s.importance_trigger_max,
            "importance_trigger_curr": s.importance_trigger_curr,
            "importance_ele_n": s.importance_ele_n,
            "thought_count": s.thought_count,
            "daily_req": s.daily_req,
            "f_daily_schedule": s.f_daily_schedule,
            "f_daily_schedule_hourly_org": s.f_daily_schedule_hourly_org,
            "act_address": s.act_address or None,
            "act_start_time": s.act_start_time.strftime("%B %d, %Y, %H:%M:%S") if s.act_start_time else None,
            "act_duration": s.act_duration,
            "act_description": s.act_description or None,
            "act_pronunciatio": s.act_pronunciatio or None,
            "act_event": s.act_event,
            "act_obj_description": s.act_obj_description or None,
            "act_obj_pronunciatio": s.act_obj_pronunciatio or None,
            "act_obj_event": s.act_obj_event,
            "chatting_with": s.chatting_with,
            "chat": s.chat,
            "chatting_with_buffer": s.chatting_with_buffer,
            "chatting_end_time": s.chatting_end_time.strftime("%B %d, %Y, %H:%M:%S") if s.chatting_end_time else None,
            "act_path_set": s.act_path_set,
            "planned_path": s.planned_path,
        }
    )
    return base


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str))
