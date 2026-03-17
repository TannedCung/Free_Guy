"""Management command to import file-based simulations into PostgreSQL and Qdrant.

Usage:
    python manage.py import_simulation <sim_code>          # import one simulation
    python manage.py import_simulation --all               # import all in storage/
    python manage.py import_simulation <sim_code> --storage-dir /path/to/storage
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime
from datetime import timezone as dt_timezone
from pathlib import Path
from typing import Any

import qdrant_utils as qu
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
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

# Default storage directory relative to manage.py location
# File: frontend_server/translator/management/commands/import_simulation.py
# parents[3] = frontend_server/ (project root where manage.py lives)
_DEFAULT_STORAGE = Path(__file__).resolve().parents[3] / "storage"


def _parse_sim_time(time_str: str) -> datetime:
    """Parse simulation time string ('February 13, 2023, 00:00:00') to UTC datetime."""
    for fmt in ["%B %d, %Y, %H:%M:%S", "%B %d, %Y"]:
        try:
            return datetime.strptime(time_str.strip(), fmt).replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse simulation time: {time_str!r}")


def _parse_node_time(time_str: Any) -> datetime | None:
    """Parse node datetime string ('2023-02-13 00:00:10') to UTC datetime, or None."""
    if not time_str:
        return None
    for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"]:
        try:
            return datetime.strptime(str(time_str).strip(), fmt).replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
    return None


def _load_json(path: Path) -> Any:
    """Load JSON from path, returning None on error."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        warnings.warn(f"Could not load {path}: {exc}", stacklevel=2)
        return None


class Command(BaseCommand):
    help = "Import file-based simulation(s) from storage/ into PostgreSQL and Qdrant."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "sim_code",
            nargs="?",
            type=str,
            default=None,
            help="Simulation directory name to import (e.g. base_the_ville_isabella_maria_klaus).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Import all simulations found in the storage directory.",
        )
        parser.add_argument(
            "--storage-dir",
            type=str,
            default=str(_DEFAULT_STORAGE),
            help=f"Path to the storage root directory (default: {_DEFAULT_STORAGE}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        storage_dir = Path(options["storage_dir"]).resolve()
        import_all: bool = options["all"]
        sim_code: str | None = options["sim_code"]

        if not import_all and not sim_code:
            raise CommandError("Provide a <sim_code> argument or use --all.")

        if not storage_dir.exists():
            raise CommandError(f"Storage directory not found: {storage_dir}")

        if import_all:
            sim_dirs = sorted(d for d in storage_dir.iterdir() if d.is_dir())
            self.stdout.write(f"Importing {len(sim_dirs)} simulation(s) from {storage_dir}")
        else:
            sim_dirs = [storage_dir / sim_code]  # type: ignore[list-item]

        for sim_dir in sim_dirs:
            if not sim_dir.is_dir():
                self.stdout.write(self.style.WARNING(f"  Skipping {sim_dir.name}: not a directory"))
                continue
            try:
                self._import_simulation(sim_dir)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ERROR importing {sim_dir.name}: {exc}"))
                logger.exception("Error importing simulation %s", sim_dir.name)

    def _import_simulation(self, sim_dir: Path) -> None:
        sim_code = sim_dir.name
        self.stdout.write(f"Importing simulation: {sim_code}")

        # ── Load meta.json ───────────────────────────────────────────────────────
        meta_path = sim_dir / "reverie" / "meta.json"
        meta: dict[str, Any] = _load_json(meta_path) or {}

        start_date: datetime | None = None
        curr_time: datetime | None = None
        try:
            if meta.get("start_date"):
                start_date = _parse_sim_time(meta["start_date"])
        except ValueError as exc:
            warnings.warn(f"Cannot parse start_date in {sim_code}: {exc}", stacklevel=2)
        try:
            if meta.get("curr_time"):
                curr_time = _parse_sim_time(meta["curr_time"])
        except ValueError as exc:
            warnings.warn(f"Cannot parse curr_time in {sim_code}: {exc}", stacklevel=2)

        n_personas = 0
        n_concept_nodes = 0
        n_embeddings = 0
        n_env_steps = 0
        n_movement_steps = 0

        with transaction.atomic():
            # ── Simulation row ───────────────────────────────────────────────────
            sim, sim_created = Simulation.objects.update_or_create(
                name=sim_code,
                defaults={
                    "fork_sim_code": meta.get("fork_sim_code") or sim_code,
                    "start_date": start_date,
                    "curr_time": curr_time,
                    "sec_per_step": meta.get("sec_per_step"),
                    "maze_name": meta.get("maze_name"),
                    "step": int(meta.get("step", 0)),
                    "status": Simulation.Status.COMPLETED,
                    "config": meta,
                },
            )
            action = "Created" if sim_created else "Updated"
            self.stdout.write(f"  {action} Simulation: {sim_code} (pk={sim.pk})")

            # ── Personas ─────────────────────────────────────────────────────────
            personas_dir = sim_dir / "personas"
            if not personas_dir.exists():
                self.stdout.write(self.style.WARNING("  No personas/ directory found."))
            else:
                for persona_dir in sorted(d for d in personas_dir.iterdir() if d.is_dir()):
                    persona_stats = self._import_persona(sim, persona_dir)
                    n_personas += 1
                    n_concept_nodes += persona_stats["concept_nodes"]
                    n_embeddings += persona_stats["embeddings"]

            # ── EnvironmentState rows ─────────────────────────────────────────────
            env_dir = sim_dir / "environment"
            if env_dir.exists():
                env_objects: list[EnvironmentState] = []
                existing_env_steps = set(EnvironmentState.objects.filter(simulation=sim).values_list("step", flat=True))
                for env_file in sorted(env_dir.glob("*.json"), key=lambda p: int(p.stem)):
                    step_num = int(env_file.stem)
                    if step_num in existing_env_steps:
                        continue
                    data = _load_json(env_file)
                    if data is None:
                        continue
                    env_objects.append(
                        EnvironmentState(
                            simulation=sim,
                            step=step_num,
                            agent_positions=data,
                        )
                    )
                    if len(env_objects) >= 500:
                        EnvironmentState.objects.bulk_create(env_objects, batch_size=500, ignore_conflicts=True)
                        n_env_steps += len(env_objects)
                        env_objects = []
                if env_objects:
                    EnvironmentState.objects.bulk_create(env_objects, batch_size=500, ignore_conflicts=True)
                    n_env_steps += len(env_objects)

            # ── MovementRecord rows ───────────────────────────────────────────────
            movement_dir = sim_dir / "movement"
            if movement_dir.exists():
                mov_objects: list[MovementRecord] = []
                existing_mov_steps = set(MovementRecord.objects.filter(simulation=sim).values_list("step", flat=True))
                for mov_file in sorted(movement_dir.glob("*.json"), key=lambda p: int(p.stem)):
                    step_num = int(mov_file.stem)
                    if step_num in existing_mov_steps:
                        continue
                    data = _load_json(mov_file)
                    if data is None:
                        continue
                    step_meta = data.get("meta", {})
                    step_time: datetime | None = None
                    try:
                        if step_meta.get("curr_time"):
                            step_time = _parse_sim_time(step_meta["curr_time"])
                    except ValueError:
                        pass
                    persona_movements: dict[str, Any] = data.get("persona", data)
                    mov_objects.append(
                        MovementRecord(
                            simulation=sim,
                            step=step_num,
                            sim_curr_time=step_time,
                            persona_movements=persona_movements,
                        )
                    )
                    if len(mov_objects) >= 500:
                        MovementRecord.objects.bulk_create(mov_objects, batch_size=500, ignore_conflicts=True)
                        n_movement_steps += len(mov_objects)
                        mov_objects = []
                if mov_objects:
                    MovementRecord.objects.bulk_create(mov_objects, batch_size=500, ignore_conflicts=True)
                    n_movement_steps += len(mov_objects)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported sim {sim_code}: {n_personas} personas, {n_concept_nodes} concept nodes, "
                f"{n_embeddings} embeddings, {n_env_steps} environment steps, {n_movement_steps} movement steps"
            )
        )

    def _import_persona(self, sim: Simulation, persona_dir: Path) -> dict[str, int]:
        """Import a single persona directory. Returns stats dict."""
        persona_name = persona_dir.name
        mem_dir = persona_dir / "bootstrap_memory"
        scratch_path = mem_dir / "scratch.json" if mem_dir.exists() else persona_dir / "scratch.json"

        scratch: dict[str, Any] = _load_json(scratch_path) or {}

        # ── Persona row ──────────────────────────────────────────────────────────
        persona, _ = Persona.objects.update_or_create(
            simulation=sim,
            name=persona_name,
            defaults={
                "first_name": scratch.get("first_name", ""),
                "last_name": scratch.get("last_name", ""),
                "age": scratch.get("age"),
                "innate": scratch.get("innate", ""),
                "learned": scratch.get("learned", ""),
                "currently": scratch.get("currently", ""),
                "lifestyle": scratch.get("lifestyle", ""),
                "living_area": scratch.get("living_area", ""),
                "daily_plan_req": scratch.get("daily_plan_req", ""),
                "status": Persona.Status.ACTIVE,
            },
        )

        # ── PersonaScratch row ───────────────────────────────────────────────────
        if scratch:
            curr_time_val: datetime | None = None
            try:
                if scratch.get("curr_time"):
                    curr_time_val = _parse_sim_time(str(scratch["curr_time"]))
            except ValueError:
                pass

            act_start_val: datetime | None = None
            try:
                if scratch.get("act_start_time"):
                    act_start_val = _parse_sim_time(str(scratch["act_start_time"]))
            except ValueError:
                pass

            chatting_end_val: datetime | None = None
            try:
                if scratch.get("chatting_end_time"):
                    chatting_end_val = _parse_sim_time(str(scratch["chatting_end_time"]))
            except ValueError:
                pass

            PersonaScratch.objects.update_or_create(
                persona=persona,
                defaults={
                    "vision_r": scratch.get("vision_r", 8),
                    "att_bandwidth": scratch.get("att_bandwidth", 8),
                    "retention": scratch.get("retention", 8),
                    "curr_time": curr_time_val,
                    "curr_tile": scratch.get("curr_tile") or [],
                    "concept_forget": scratch.get("concept_forget", 100),
                    "daily_reflection_time": scratch.get("daily_reflection_time", 180),
                    "daily_reflection_size": scratch.get("daily_reflection_size", 5),
                    "overlap_reflect_th": scratch.get("overlap_reflect_th", 4),
                    "kw_strg_event_reflect_th": scratch.get("kw_strg_event_reflect_th", 10),
                    "kw_strg_thought_reflect_th": scratch.get("kw_strg_thought_reflect_th", 9),
                    "recency_w": scratch.get("recency_w", 1.0),
                    "relevance_w": scratch.get("relevance_w", 1.0),
                    "importance_w": scratch.get("importance_w", 1.0),
                    "recency_decay": scratch.get("recency_decay", 0.995),
                    "importance_trigger_max": scratch.get("importance_trigger_max", 150),
                    "importance_trigger_curr": scratch.get("importance_trigger_curr", 150),
                    "importance_ele_n": scratch.get("importance_ele_n", 0),
                    "thought_count": scratch.get("thought_count", 5),
                    "daily_req": scratch.get("daily_req") or [],
                    "f_daily_schedule": scratch.get("f_daily_schedule") or [],
                    "f_daily_schedule_hourly_org": scratch.get("f_daily_schedule_hourly_org") or [],
                    "act_address": scratch.get("act_address") or "",
                    "act_start_time": act_start_val,
                    "act_duration": scratch.get("act_duration"),
                    "act_description": scratch.get("act_description") or "",
                    "act_pronunciatio": scratch.get("act_pronunciatio") or "",
                    "act_event": scratch.get("act_event") or [],
                    "act_obj_description": scratch.get("act_obj_description") or "",
                    "act_obj_pronunciatio": scratch.get("act_obj_pronunciatio") or "",
                    "act_obj_event": scratch.get("act_obj_event") or [],
                    "chatting_with": scratch.get("chatting_with"),
                    "chat": scratch.get("chat"),
                    "chatting_with_buffer": scratch.get("chatting_with_buffer") or {},
                    "chatting_end_time": chatting_end_val,
                    "act_path_set": bool(scratch.get("act_path_set", False)),
                    "planned_path": scratch.get("planned_path") or [],
                },
            )

        # ── SpatialMemory row ────────────────────────────────────────────────────
        spatial_path = (mem_dir / "spatial_memory.json") if mem_dir.exists() else persona_dir / "spatial_memory.json"
        spatial_data = _load_json(spatial_path)
        if spatial_data is not None:
            SpatialMemory.objects.update_or_create(persona=persona, defaults={"tree": spatial_data})

        # ── ConceptNode rows ─────────────────────────────────────────────────────
        am_dir = (mem_dir / "associative_memory") if mem_dir.exists() else persona_dir / "associative_memory"
        nodes_path = am_dir / "nodes.json"
        nodes_data: dict[str, Any] = _load_json(nodes_path) or {}
        n_concept_nodes = 0

        if nodes_data:
            existing_node_ids = set(ConceptNode.objects.filter(persona=persona).values_list("node_id", flat=True))
            node_objects: list[ConceptNode] = []
            for node_key, node in nodes_data.items():
                # node_key is "node_9" → node_id = 9
                try:
                    node_id = int(node_key.replace("node_", ""))
                except ValueError:
                    warnings.warn(f"Cannot parse node_id from key {node_key!r}", stacklevel=2)
                    continue
                if node_id in existing_node_ids:
                    continue
                raw_type = node.get("type", "event")
                if raw_type not in ("event", "thought", "chat"):
                    raw_type = "event"
                node_objects.append(
                    ConceptNode(
                        persona=persona,
                        node_id=node_id,
                        node_count=node.get("node_count", 0),
                        type_count=node.get("type_count", 0),
                        node_type=raw_type,
                        depth=node.get("depth", 0),
                        created=_parse_node_time(node.get("created")),
                        expiration=_parse_node_time(node.get("expiration")),
                        last_accessed=_parse_node_time(node.get("last_accessed")),
                        subject=node.get("subject", ""),
                        predicate=node.get("predicate", ""),
                        object=node.get("object", ""),
                        description=node.get("description", ""),
                        embedding_key=node.get("embedding_key", ""),
                        poignancy=float(node.get("poignancy", 0.0)),
                        keywords=node.get("keywords") or [],
                        filling=node.get("filling") or [],
                    )
                )
                if len(node_objects) >= 500:
                    ConceptNode.objects.bulk_create(node_objects, batch_size=500, ignore_conflicts=True)
                    n_concept_nodes += len(node_objects)
                    node_objects = []
            if node_objects:
                ConceptNode.objects.bulk_create(node_objects, batch_size=500, ignore_conflicts=True)
                n_concept_nodes += len(node_objects)

        # ── KeywordStrength rows ─────────────────────────────────────────────────
        kw_path = am_dir / "kw_strength.json"
        kw_data: dict[str, Any] = _load_json(kw_path) or {}
        kw_objects: list[KeywordStrength] = []

        if kw_data:
            existing_kw = set(KeywordStrength.objects.filter(persona=persona).values_list("keyword", "strength_type"))
            for kw, strength in (kw_data.get("kw_strength_event") or {}).items():
                if (kw, "event") not in existing_kw:
                    kw_objects.append(
                        KeywordStrength(persona=persona, keyword=kw, strength_type="event", strength=int(strength))
                    )
            for kw, strength in (kw_data.get("kw_strength_thought") or {}).items():
                if (kw, "thought") not in existing_kw:
                    kw_objects.append(
                        KeywordStrength(persona=persona, keyword=kw, strength_type="thought", strength=int(strength))
                    )
            if kw_objects:
                KeywordStrength.objects.bulk_create(kw_objects, batch_size=500, ignore_conflicts=True)

        # ── Embeddings → Qdrant ──────────────────────────────────────────────────
        embeddings_path = am_dir / "embeddings.json"
        embeddings_data: dict[str, Any] = _load_json(embeddings_path) or {}
        n_embeddings = 0
        if embeddings_data:
            try:
                n_embeddings = qu.batch_store_embeddings(
                    persona_id=persona.pk,
                    simulation_id=sim.pk,
                    embeddings=embeddings_data,
                )
            except Exception as exc:
                warnings.warn(f"Qdrant upsert failed for {persona_name}: {exc}", stacklevel=2)

        return {"concept_nodes": n_concept_nodes, "embeddings": n_embeddings}
