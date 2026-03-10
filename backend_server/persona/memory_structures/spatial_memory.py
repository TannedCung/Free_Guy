"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: spatial_memory.py
Description: Defines the MemoryTree class that serves as the agents' spatial
memory that aids in grounding their behavior in the game world.
"""

from __future__ import annotations

import json
from typing import Any

from global_methods import check_if_file_exists


class MemoryTree:
    tree: dict[str, Any]

    def __init__(self, f_saved: str) -> None:
        self.tree = {}
        if check_if_file_exists(f_saved):
            self.tree = json.load(open(f_saved))

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

    def save(self, out_json: str) -> None:
        with open(out_json, "w") as outfile:
            json.dump(self.tree, outfile)

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
