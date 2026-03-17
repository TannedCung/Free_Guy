"""Management command to import compressed demo data into PostgreSQL.

Usage:
    python manage.py import_demo <demo_code>          # import one demo
    python manage.py import_demo --all                # import all in compressed_storage/
    python manage.py import_demo <demo_code> --compressed-dir /path/to/compressed_storage
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime
from datetime import timezone as dt_timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from translator.models import Demo, DemoMovement

logger = logging.getLogger(__name__)

# Default compressed_storage directory relative to manage.py
# File: frontend_server/translator/management/commands/import_demo.py
# parents[3] = frontend_server/ (project root where manage.py lives)
_DEFAULT_COMPRESSED = Path(__file__).resolve().parents[3] / "compressed_storage"


def _parse_sim_time(time_str: str) -> datetime:
    """Parse simulation time string ('February 13, 2023, 00:00:00') to UTC datetime."""
    for fmt in ["%B %d, %Y, %H:%M:%S", "%B %d, %Y"]:
        try:
            return datetime.strptime(time_str.strip(), fmt).replace(tzinfo=dt_timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse simulation time: {time_str!r}")


def _load_json(path: Path) -> Any:
    """Load JSON from path, returning None on error with a warning."""
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as exc:
        warnings.warn(f"Could not load {path}: {exc}", stacklevel=2)
        return None


class Command(BaseCommand):
    help = "Import compressed demo(s) from compressed_storage/ into PostgreSQL."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "demo_code",
            nargs="?",
            type=str,
            default=None,
            help="Demo directory name to import.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            default=False,
            help="Import all demos found in the compressed storage directory.",
        )
        parser.add_argument(
            "--compressed-dir",
            type=str,
            default=str(_DEFAULT_COMPRESSED),
            help=f"Path to the compressed_storage root (default: {_DEFAULT_COMPRESSED}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        compressed_dir = Path(options["compressed_dir"]).resolve()
        import_all: bool = options["all"]
        demo_code: str | None = options["demo_code"]

        if not import_all and not demo_code:
            raise CommandError("Provide a <demo_code> argument or use --all.")

        if not compressed_dir.exists():
            raise CommandError(f"Compressed storage directory not found: {compressed_dir}")

        if import_all:
            demo_dirs = sorted(d for d in compressed_dir.iterdir() if d.is_dir())
            self.stdout.write(f"Importing {len(demo_dirs)} demo(s) from {compressed_dir}")
        else:
            demo_dirs = [compressed_dir / demo_code]  # type: ignore[list-item]

        for demo_dir in demo_dirs:
            if not demo_dir.is_dir():
                self.stdout.write(self.style.WARNING(f"  Skipping {demo_dir.name}: not a directory"))
                continue
            try:
                self._import_demo(demo_dir)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"  ERROR importing {demo_dir.name}: {exc}"))
                logger.exception("Error importing demo %s", demo_dir.name)

    def _import_demo(self, demo_dir: Path) -> None:
        demo_code = demo_dir.name
        self.stdout.write(f"Importing demo: {demo_code}")

        # ── Load meta.json ─────────────────────────────────────────────────────
        meta_path = demo_dir / "meta.json"
        meta: dict[str, Any] = _load_json(meta_path) or {}

        start_date: datetime | None = None
        curr_time: datetime | None = None
        try:
            if meta.get("start_date"):
                start_date = _parse_sim_time(meta["start_date"])
        except ValueError as exc:
            warnings.warn(f"Cannot parse start_date in {demo_code}: {exc}", stacklevel=2)
        try:
            if meta.get("curr_time"):
                curr_time = _parse_sim_time(meta["curr_time"])
        except ValueError as exc:
            warnings.warn(f"Cannot parse curr_time in {demo_code}: {exc}", stacklevel=2)

        # ── Load master_movement.json ──────────────────────────────────────────
        movement_path = demo_dir / "master_movement.json"
        master_movement: dict[str, Any] = _load_json(movement_path) or {}
        total_steps = len(master_movement)

        with transaction.atomic():
            # ── Demo row ───────────────────────────────────────────────────────
            demo, demo_created = Demo.objects.update_or_create(
                name=demo_code,
                defaults={
                    "fork_sim_code": meta.get("fork_sim_code") or demo_code,
                    "start_date": start_date,
                    "curr_time": curr_time,
                    "sec_per_step": meta.get("sec_per_step"),
                    "maze_name": meta.get("maze_name"),
                    "persona_names": meta.get("persona_names") or [],
                    "step": int(meta.get("step", total_steps)),
                    "total_steps": total_steps,
                },
            )
            action = "Created" if demo_created else "Updated"
            self.stdout.write(f"  {action} Demo: {demo_code} (pk={demo.pk}, total_steps={total_steps})")

            # ── DemoMovement rows ──────────────────────────────────────────────
            existing_steps = set(DemoMovement.objects.filter(demo=demo).values_list("step", flat=True))
            movement_objects: list[DemoMovement] = []

            for step_key, agent_movements in master_movement.items():
                try:
                    step_num = int(step_key)
                except ValueError:
                    warnings.warn(f"Cannot parse step key {step_key!r} in {demo_code}", stacklevel=2)
                    continue
                if step_num in existing_steps:
                    continue
                movement_objects.append(
                    DemoMovement(
                        demo=demo,
                        step=step_num,
                        agent_movements=agent_movements,
                    )
                )
                if len(movement_objects) >= 500:
                    DemoMovement.objects.bulk_create(movement_objects, batch_size=500, ignore_conflicts=True)
                    movement_objects = []

            if movement_objects:
                DemoMovement.objects.bulk_create(movement_objects, batch_size=500, ignore_conflicts=True)

        n_imported = total_steps - len(existing_steps) if not demo_created else total_steps
        self.stdout.write(self.style.SUCCESS(f"Imported demo {demo_code}: {n_imported} movement steps"))
