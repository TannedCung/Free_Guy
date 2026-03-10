"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: perceive.py
Description: This defines the "Perceive" module for generative agents.
"""

from __future__ import annotations

import math
from operator import itemgetter
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from maze import Maze
    from persona.persona import Persona

# from persona.prompt_template.gpt_structure import *
from persona.memory_structures.associative_memory import ConceptNode
from persona.prompt_template.llm_bridge import get_embedding
from persona.prompt_template.prompts.conversation import run_gpt_prompt_chat_poignancy
from persona.prompt_template.prompts.perception import run_gpt_prompt_event_poignancy


def generate_poig_score(persona: Persona, event_type: str, description: str) -> Optional[int]:
    if "is idle" in description:
        return 1

    if event_type == "event":
        return run_gpt_prompt_event_poignancy(persona, description)[0]
    elif event_type == "chat":
        return run_gpt_prompt_chat_poignancy(persona, persona.scratch.act_description)[0]
    return None


def perceive(persona: Persona, maze: Maze) -> list[ConceptNode]:
    """
    Perceives events around the persona and saves it to the memory, both events
    and spaces.

    We first perceive the events nearby the persona, as determined by its
    <vision_r>. If there are a lot of events happening within that radius, we
    take the <att_bandwidth> of the closest events. Finally, we check whether
    any of them are new, as determined by <retention>. If they are new, then we
    save those and return the <ConceptNode> instances for those events.

    INPUT:
      persona: An instance of <Persona> that represents the current persona.
      maze: An instance of <Maze> that represents the current maze in which the
            persona is acting in.
    OUTPUT:
      ret_events: a list of <ConceptNode> that are perceived and new.
    """
    # PERCEIVE SPACE
    # We get the nearby tiles given our current tile and the persona's vision
    # radius.
    nearby_tiles = maze.get_nearby_tiles(
        persona.scratch.curr_tile,  # type: ignore[arg-type]
        persona.scratch.vision_r,
    )

    # We then store the perceived space. Note that the s_mem of the persona is
    # in the form of a tree constructed using dictionaries.
    for tile_coord in nearby_tiles:
        tile_det = maze.access_tile(tile_coord)
        if tile_det["world"]:
            if tile_det["world"] not in persona.s_mem.tree:
                persona.s_mem.tree[tile_det["world"]] = {}
        if tile_det["sector"]:
            if tile_det["sector"] not in persona.s_mem.tree[tile_det["world"]]:
                persona.s_mem.tree[tile_det["world"]][tile_det["sector"]] = {}
        if tile_det["arena"]:
            if tile_det["arena"] not in persona.s_mem.tree[tile_det["world"]][tile_det["sector"]]:
                persona.s_mem.tree[tile_det["world"]][tile_det["sector"]][tile_det["arena"]] = []
        if tile_det["game_object"]:
            if (
                tile_det["game_object"]
                not in persona.s_mem.tree[tile_det["world"]][tile_det["sector"]][tile_det["arena"]]
            ):
                persona.s_mem.tree[tile_det["world"]][tile_det["sector"]][tile_det["arena"]] += [
                    tile_det["game_object"]
                ]

    # PERCEIVE EVENTS.
    # We will perceive events that take place in the same arena as the
    # persona's current arena.
    curr_arena_path = maze.get_tile_path(persona.scratch.curr_tile, "arena")  # type: ignore[arg-type]
    # We do not perceive the same event twice (this can happen if an object is
    # extended across multiple tiles).
    percept_events_set = set()
    # We will order our percept based on the distance, with the closest ones
    # getting priorities.
    percept_events_list = []
    # First, we put all events that are occuring in the nearby tiles into the
    # percept_events_list
    for tile in nearby_tiles:
        tile_details = maze.access_tile(tile)
        if tile_details["events"]:
            if maze.get_tile_path(tile, "arena") == curr_arena_path:
                # This calculates the distance between the persona's current tile,
                # and the target tile.
                dist = math.dist(
                    [tile[0], tile[1]],
                    [
                        persona.scratch.curr_tile[0],  # type: ignore[index]
                        persona.scratch.curr_tile[1],  # type: ignore[index]
                    ],
                )
                # Add any relevant events to our temp set/list with the distant info.
                for event in tile_details["events"]:
                    if event not in percept_events_set:
                        percept_events_list += [[dist, event]]
                        percept_events_set.add(event)

    # We sort, and perceive only persona.scratch.att_bandwidth of the closest
    # events. If the bandwidth is larger, then it means the persona can perceive
    # more elements within a small area.
    percept_events_list = sorted(percept_events_list, key=itemgetter(0))
    perceived_events = []
    for dist, event in percept_events_list[: persona.scratch.att_bandwidth]:
        perceived_events += [event]

    # Storing events.
    # <ret_events> is a list of <ConceptNode> instances from the persona's
    # associative memory.
    ret_events = []
    for p_event in perceived_events:
        s, p, o, desc = p_event
        if not p:
            # If the object is not present, then we default the event to "idle".
            p = "is"
            o = "idle"
            desc = "idle"
        desc = f"{s.split(':')[-1]} is {desc}"
        p_event = (s, p, o)

        # We retrieve the latest persona.scratch.retention events. If there is
        # something new that is happening (that is, p_event not in latest_events),
        # then we add that event to the a_mem and return it.
        latest_events = persona.a_mem.get_summarized_latest_events(persona.scratch.retention)
        if p_event not in latest_events:
            # We start by managing keywords.
            keywords = set()
            sub = p_event[0]
            obj = p_event[2]
            if ":" in p_event[0]:
                sub = p_event[0].split(":")[-1]
            if ":" in p_event[2]:
                obj = p_event[2].split(":")[-1]
            keywords.update([sub, obj])

            # Get event embedding
            desc_embedding_in = desc
            if "(" in desc:
                desc_embedding_in = desc_embedding_in.split("(")[1].split(")")[0].strip()
            if desc_embedding_in in persona.a_mem.embeddings:
                event_embedding = persona.a_mem.embeddings[desc_embedding_in]
            else:
                event_embedding = get_embedding(desc_embedding_in)
            event_embedding_pair = (desc_embedding_in, event_embedding)

            # Get event poignancy.
            event_poignancy = generate_poig_score(persona, "event", desc_embedding_in)

            # If we observe the persona's self chat, we include that in the memory
            # of the persona here.
            chat_node_ids = []
            if p_event[0] == f"{persona.name}" and p_event[1] == "chat with":
                curr_event = persona.scratch.act_event
                if persona.scratch.act_description in persona.a_mem.embeddings:
                    chat_embedding = persona.a_mem.embeddings[persona.scratch.act_description]
                else:
                    chat_embedding = get_embedding(persona.scratch.act_description)  # type: ignore[arg-type]
                chat_embedding_pair = (persona.scratch.act_description, chat_embedding)
                chat_poignancy = generate_poig_score(persona, "chat", persona.scratch.act_description)  # type: ignore[arg-type]
                chat_node = persona.a_mem.add_chat(
                    persona.scratch.curr_time,  # type: ignore[arg-type]
                    None,
                    curr_event[0],  # type: ignore[arg-type]
                    curr_event[1],  # type: ignore[arg-type]
                    curr_event[2],  # type: ignore[arg-type]
                    persona.scratch.act_description,  # type: ignore[arg-type]
                    keywords,  # type: ignore[arg-type]
                    chat_poignancy,  # type: ignore[arg-type]
                    chat_embedding_pair,  # type: ignore[arg-type]
                    persona.scratch.chat,  # type: ignore[arg-type]
                )
                chat_node_ids = [chat_node.node_id]

            # Finally, we add the current event to the agent's memory.
            ret_events += [
                persona.a_mem.add_event(
                    persona.scratch.curr_time,  # type: ignore[arg-type]
                    None,
                    s,
                    p,
                    o,
                    desc,
                    keywords,
                    event_poignancy,  # type: ignore[arg-type]
                    event_embedding_pair,
                    chat_node_ids,
                )
            ]  # type: ignore[arg-type]
            persona.scratch.importance_trigger_curr -= event_poignancy  # type: ignore[operator]
            persona.scratch.importance_ele_n += 1

    return ret_events
