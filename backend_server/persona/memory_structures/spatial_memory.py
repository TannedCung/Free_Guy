"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: spatial_memory.py
Description: Defines the MemoryTree class that serves as the agents' spatial
memory that aids in grounding their behavior in the game world.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from global_methods import check_if_file_exists

logger = logging.getLogger(__name__)


class MemoryTree:
    tree: dict[str, Any]

    def __init__(self, f_saved: Optional[str] = None, persona_id: Optional[int] = None) -> None:
        self._persona_id: Optional[int] = persona_id
        self.tree = {}

        if persona_id is not None:
            self._load_from_db(persona_id)
        elif f_saved is not None and check_if_file_exists(f_saved):
            self.tree = json.load(open(f_saved))

    # ── DB persistence ─────────────────────────────────────────────────────────

    def _load_from_db(self, persona_id: int) -> None:
        """Load tree JSONB from SpatialMemory row; creates the row if missing."""
        try:
            from translator.models import SpatialMemory as SpatialMemoryModel

            obj, _ = SpatialMemoryModel.objects.get_or_create(
                persona_id=persona_id,
                defaults={"tree": {}},
            )
            self.tree = obj.tree or {}
        except Exception as exc:
            logger.warning("Could not load SpatialMemory from DB for persona %s: %s", persona_id, exc)

    def save(self, out_json: Optional[str] = None) -> None:
        """Save tree to DB (DB mode) or to a JSON file (legacy mode)."""
        if out_json is None:
            # DB mode
            if self._persona_id is not None:
                self._save_to_db()
            return

        # Legacy file-based save
        with open(out_json, "w") as outfile:
            json.dump(self.tree, outfile)

    def _save_to_db(self) -> None:
        """Write tree JSONB to SpatialMemory row via Django ORM."""
        if self._persona_id is None:
            return
        try:
            from translator.models import SpatialMemory as SpatialMemoryModel

            SpatialMemoryModel.objects.update_or_create(
                persona_id=self._persona_id,
                defaults={"tree": self.tree},
            )
        except Exception as exc:
            logger.warning("Could not save SpatialMemory to DB for persona %s: %s", self._persona_id, exc)

    # ── Tree navigation ────────────────────────────────────────────────────────

    def print_tree(self) -> None:
        def _print_tree(tree: Any, depth: int) -> None:
            dash = " >" * depth
            if isinstance(tree, list):
                if tree:
                    print(dash, tree)
                return

            for key, val in tree.items():
                if key:
                    print(dash, key)
                _print_tree(val, depth + 1)

        _print_tree(self.tree, 0)

    def get_str_accessible_sectors(self, curr_world: str) -> str:
        """
        Returns a summary string of all the arenas that the persona can access
        within the current sector.

        Note that there are places a given persona cannot enter. This information
        is provided in the persona sheet. We account for this in this function.

        INPUT
          None
        OUTPUT
          A summary string of all the arenas that the persona can access.
        EXAMPLE STR OUTPUT
          "bedroom, kitchen, dining room, office, bathroom"
        """
        x = ", ".join(list(self.tree[curr_world].keys()))
        return x

    def get_str_accessible_sector_arenas(self, sector: str) -> str:
        """
        Returns a summary string of all the arenas that the persona can access
        within the current sector.

        Note that there are places a given persona cannot enter. This information
        is provided in the persona sheet. We account for this in this function.

        INPUT
          None
        OUTPUT
          A summary string of all the arenas that the persona can access.
        EXAMPLE STR OUTPUT
          "bedroom, kitchen, dining room, office, bathroom"
        """
        curr_world, curr_sector = sector.split(":")
        if not curr_sector:
            return ""
        x = ", ".join(list(self.tree[curr_world][curr_sector].keys()))
        return x

    def get_str_accessible_arena_game_objects(self, arena: str) -> str:
        """
        Get a str list of all accessible game objects that are in the arena. If
        temp_address is specified, we return the objects that are available in
        that arena, and if not, we return the objects that are in the arena our
        persona is currently in.

        INPUT
          temp_address: optional arena address
        OUTPUT
          str list of all accessible game objects in the gmae arena.
        EXAMPLE STR OUTPUT
          "phone, charger, bed, nightstand"
        """
        curr_world, curr_sector, curr_arena = arena.split(":")

        if not curr_arena:
            return ""

        try:
            x = ", ".join(list(self.tree[curr_world][curr_sector][curr_arena]))
        except KeyError:
            x = ", ".join(list(self.tree[curr_world][curr_sector][curr_arena.lower()]))
        return x


if __name__ == "__main__":
    x_path = "../../../..//frontend_server/storage/the_ville_base_LinFamily/personas/Eddy Lin/bootstrap_memory/spatial_memory.json"
    x = MemoryTree(x_path)
    x.print_tree()

    print(x.get_str_accessible_sector_arenas("dolores double studio:double studio"))
