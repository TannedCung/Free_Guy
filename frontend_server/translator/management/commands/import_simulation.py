"""Management command to import JSON simulation data into PostgreSQL/SQLite."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from datetime import timezone as dt_timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from translator.models import Agent, AgentMemory, Conversation, Simulation, SimulationStep

logger = logging.getLogger(__name__)


def _parse_sim_time(time_str: str) -> datetime:
    """Parse simulation time string to datetime (returns UTC-aware datetime)."""
    try:
        dt = datetime.strptime(time_str, "%B %d, %Y, %H:%M:%S")
    except ValueError:
        dt = datetime.strptime(time_str, "%B %d, %Y")
    return dt.replace(tzinfo=dt_timezone.utc)


class Command(BaseCommand):
    help = "Import a simulation directory from JSON files into the database."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "sim_dir",
            type=str,
            help="Path to the simulation directory (e.g., frontend_server/storage/base_the_ville_...)",
        )
        parser.add_argument(
            "--description",
            type=str,
            default="",
            help="Optional description for the simulation.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        sim_dir = Path(options["sim_dir"]).resolve()
        if not sim_dir.exists() or not sim_dir.is_dir():
            raise CommandError(f"Directory does not exist: {sim_dir}")

        sim_name = sim_dir.name
        self.stdout.write(f"Importing simulation: {sim_name}")

        # --- Read reverie meta ---
        meta_path = sim_dir / "reverie" / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            self.stdout.write(f"  Loaded meta: step={meta.get('step', 0)}")

        # --- Create or update Simulation record ---
        simulation, created = Simulation.objects.get_or_create(
            name=sim_name,
            defaults={
                "description": options["description"],
                "status": Simulation.Status.COMPLETED,
                "config": meta,
            },
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"  Created Simulation: {sim_name}"))
        else:
            self.stdout.write(f"  Simulation already exists: {sim_name} (skipping re-create)")

        # --- Import personas ---
        personas_dir = sim_dir / "personas"
        if not personas_dir.exists():
            self.stdout.write(self.style.WARNING("  No personas/ directory found."))
        else:
            persona_dirs = [p for p in personas_dir.iterdir() if p.is_dir()]
            self.stdout.write(f"  Found {len(persona_dirs)} persona(s).")
            for persona_dir in persona_dirs:
                self._import_persona(simulation, persona_dir)

        # --- Import simulation steps from movement/ ---
        movement_dir = sim_dir / "movement"
        if not movement_dir.exists():
            self.stdout.write("  No movement/ directory; skipping steps.")
        else:
            movement_files = sorted(movement_dir.glob("*.json"), key=lambda p: int(p.stem))
            self.stdout.write(f"  Found {len(movement_files)} movement step(s).")
            for step_file in movement_files:
                self._import_step(simulation, step_file)

        # --- Import conversations from movement/ (chat data embedded in steps) ---
        # Conversations are extracted during step import above.

        self.stdout.write(self.style.SUCCESS(f"Import complete for: {sim_name}"))

    def _import_persona(self, simulation: Simulation, persona_dir: Path) -> None:
        persona_name = persona_dir.name
        self.stdout.write(f"    Importing persona: {persona_name}")

        # Find the most recent scratch.json (bootstrap_memory or direct)
        scratch_path = persona_dir / "bootstrap_memory" / "scratch.json"
        if not scratch_path.exists():
            scratch_path = persona_dir / "scratch.json"

        scratch: dict[str, Any] = {}
        if scratch_path.exists():
            with open(scratch_path) as f:
                scratch = json.load(f)

        # Extract personality traits from innate + learned + currently
        personality_parts = []
        for key in ("innate", "learned", "currently"):
            if scratch.get(key):
                personality_parts.append(scratch[key])
        personality_traits = "\n".join(personality_parts)

        # Determine current location
        current_location = scratch.get("living_area", "")

        # Get or create Agent
        agent, created = Agent.objects.get_or_create(
            simulation=simulation,
            name=persona_name,
            defaults={
                "personality_traits": personality_traits,
                "current_location": current_location,
                "status": Agent.Status.IDLE,
            },
        )
        if not created:
            self.stdout.write(f"      Agent {persona_name} already exists, skipping.")
            return

        self.stdout.write(self.style.SUCCESS(f"      Created Agent: {persona_name}"))

        # Import associative memory nodes
        mem_path = persona_dir / "bootstrap_memory" / "associative_memory" / "nodes.json"
        if not mem_path.exists():
            mem_path = persona_dir / "associative_memory" / "nodes.json"

        if mem_path.exists():
            self._import_memories(agent, mem_path)

    def _import_memories(self, agent: Agent, nodes_path: Path) -> None:
        with open(nodes_path) as f:
            nodes: dict[str, Any] = json.load(f)

        if not nodes:
            return

        memory_objects: list[AgentMemory] = []
        for _node_id, node in nodes.items():
            node_type = node.get("type", "event")
            # Map node types to AgentMemory.MemoryType choices
            if node_type == "thought":
                memory_type = AgentMemory.MemoryType.THOUGHT
            elif node_type == "chat":
                memory_type = AgentMemory.MemoryType.CHAT
            else:
                memory_type = AgentMemory.MemoryType.EVENT

            content = node.get("description", "")
            importance_score = float(node.get("poignancy", 0.0))

            memory_objects.append(
                AgentMemory(
                    agent=agent,
                    memory_type=memory_type,
                    content=content,
                    importance_score=importance_score,
                )
            )

        if memory_objects:
            AgentMemory.objects.bulk_create(memory_objects)
            self.stdout.write(f"        Imported {len(memory_objects)} memory node(s).")

    def _import_step(self, simulation: Simulation, step_file: Path) -> None:
        step_number = int(step_file.stem)
        with open(step_file) as f:
            step_data: dict[str, Any] = json.load(f)

        meta = step_data.get("meta", {})
        curr_time_str = meta.get("curr_time", "")
        try:
            step_timestamp = _parse_sim_time(curr_time_str) if curr_time_str else timezone.now()
        except ValueError:
            step_timestamp = timezone.now()

        # get_or_create to be idempotent
        _, created = SimulationStep.objects.get_or_create(
            simulation=simulation,
            step_number=step_number,
            defaults={
                "timestamp": step_timestamp,
                "world_state": step_data,
            },
        )
        if created:
            self.stdout.write(f"    Imported step {step_number}")

        # Extract conversations from persona chat data in this step
        persona_data: dict[str, Any] = step_data.get("persona", {})
        self._extract_conversations(simulation, step_number, step_timestamp, persona_data)

    def _extract_conversations(
        self,
        simulation: Simulation,
        step_number: int,
        timestamp: datetime,
        persona_data: dict[str, Any],
    ) -> None:
        """Extract conversation transcripts from movement step data."""
        for persona_name, pdata in persona_data.items():
            chat = pdata.get("chat")
            if not chat:
                continue

            # Build a unique identifier for this conversation
            # Use step_number + persona_name as part of lookup
            transcript = chat if isinstance(chat, list) else [chat]

            # Avoid duplicates: check by simulation + started_at + transcript
            if Conversation.objects.filter(
                simulation=simulation,
                started_at=timestamp,
                transcript=transcript,
            ).exists():
                continue

            conv = Conversation.objects.create(
                simulation=simulation,
                started_at=timestamp,
                transcript=transcript,
            )

            # Link participants
            try:
                agent = Agent.objects.get(simulation=simulation, name=persona_name)
                conv.participants.add(agent)
            except Agent.DoesNotExist:
                pass
