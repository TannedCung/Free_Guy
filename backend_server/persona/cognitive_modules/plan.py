"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: plan.py
Description: Main planning coordinator for generative agents.
This module re-exports all planning functions from the sub-modules and
provides the top-level plan() function that orchestrates the full planning
loop for each simulation step.

Sub-modules:
  daily_planning   -- wake-up, daily/hourly schedule, task decomposition
  action_planning  -- action sector/arena/object selection, _determine_action
  reaction_planning -- conversation, reaction decisions, _should_react, _chat_react
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
    from maze import Maze
    from persona.persona import Persona

# Re-exports for backwards compatibility
from persona.cognitive_modules.action_planning import (
    _determine_action,
    generate_act_obj_desc,
    generate_act_obj_event_triple,
    generate_action_arena,
    generate_action_event_triple,
    generate_action_game_object,
    generate_action_pronunciatio,
    generate_action_sector,
)
from persona.cognitive_modules.daily_planning import (
    _long_term_planning,
    generate_first_daily_plan,
    generate_hourly_schedule,
    generate_new_decomp_schedule,
    generate_task_decomp,
    generate_wake_up_hour,
    revise_identity,
)
from persona.cognitive_modules.reaction_planning import (
    _chat_react,
    _choose_retrieved,
    _create_react,
    _should_react,
    _wait_react,
    generate_convo,
    generate_convo_summary,
    generate_decide_to_react,
    generate_decide_to_talk,
)

__all__ = [
    # daily_planning
    "generate_wake_up_hour",
    "generate_first_daily_plan",
    "generate_hourly_schedule",
    "generate_task_decomp",
    "generate_new_decomp_schedule",
    "revise_identity",
    "_long_term_planning",
    # action_planning
    "generate_action_sector",
    "generate_action_arena",
    "generate_action_game_object",
    "generate_action_pronunciatio",
    "generate_action_event_triple",
    "generate_act_obj_desc",
    "generate_act_obj_event_triple",
    "_determine_action",
    # reaction_planning
    "generate_convo",
    "generate_convo_summary",
    "generate_decide_to_talk",
    "generate_decide_to_react",
    "_choose_retrieved",
    "_should_react",
    "_create_react",
    "_chat_react",
    "_wait_react",
    # coordinator
    "plan",
]


def plan(
    persona: Persona, maze: Maze, personas: dict[str, Persona], new_day: Union[str, bool], retrieved: dict[str, Any]
) -> Optional[str]:
    """
    Main cognitive function of the chain. It takes the retrieved memory and
    perception, as well as the maze and the first day state to conduct both
    the long term and short term planning for the persona.

    INPUT:
      maze: Current <Maze> instance of the world.
      personas: A dictionary that contains all persona names as keys, and the
                Persona instance as values.
      new_day: This can take one of the three values.
        1) <Boolean> False -- It is not a "new day" cycle (if it is, we would
           need to call the long term planning sequence for the persona).
        2) <String> "First day" -- It is literally the start of a simulation,
           so not only is it a new day, but also it is the first day.
        2) <String> "New day" -- It is a new day.
      retrieved: dictionary of dictionary. The first layer specifies an event,
                 while the latter layer specifies the "curr_event", "events",
                 and "thoughts" that are relevant.
    OUTPUT
      The target action address of the persona (persona.scratch.act_address).
    """
    # PART 1: Generate the hourly schedule.
    if new_day:
        _long_term_planning(persona, new_day)

    # PART 2: If the current action has expired, we want to create a new plan.
    if persona.scratch.act_check_finished():
        _determine_action(persona, maze)

    # PART 3: If you perceived an event that needs to be responded to (saw
    # another persona), and retrieved relevant information.
    # Step 1: Retrieved may have multiple events represented in it. The first
    #         job here is to determine which of the events we want to focus
    #         on for the persona.
    #         <focused_event> takes the form of a dictionary like this:
    #         dictionary {["curr_event"] = <ConceptNode>,
    #                     ["events"] = [<ConceptNode>, ...],
    #                     ["thoughts"] = [<ConceptNode>, ...]}
    focused_event: Optional[dict[str, Any]] = None
    if retrieved.keys():
        focused_event = _choose_retrieved(persona, retrieved)

    # Step 2: Once we choose an event, we need to determine whether the
    #         persona will take any actions for the perceived event. There are
    #         three possible modes of reaction returned by _should_react.
    #         a) "chat with {target_persona.name}"
    #         b) "react"
    #         c) False
    if focused_event:
        reaction_mode = _should_react(persona, focused_event, personas)
        if reaction_mode and isinstance(reaction_mode, str):
            # If we do want to chat, then we generate conversation
            if reaction_mode[:9] == "chat with":
                _chat_react(maze, persona, focused_event, reaction_mode, personas)
            elif reaction_mode[:4] == "wait":
                _wait_react(persona, reaction_mode)

    # Step 3: Chat-related state clean up.
    # If the persona is not chatting with anyone, we clean up any of the
    # chat-related states here.
    if persona.scratch.act_event[1] != "chat with":
        persona.scratch.chatting_with = None
        persona.scratch.chat = None
        persona.scratch.chatting_end_time = None
    # We want to make sure that the persona does not keep conversing with each
    # other in an infinite loop. So, chatting_with_buffer maintains a form of
    # buffer that makes the persona wait from talking to the same target
    # immediately after chatting once. We keep track of the buffer value here.
    curr_persona_chat_buffer = persona.scratch.chatting_with_buffer
    for persona_name, buffer_count in curr_persona_chat_buffer.items():
        if persona_name != persona.scratch.chatting_with:
            persona.scratch.chatting_with_buffer[persona_name] -= 1

    return persona.scratch.act_address
