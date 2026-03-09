"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: action_planning.py
Description: Action planning functions for generative agents.
Handles determining what action the persona will take next: sector/arena/object
selection, pronunciatio (emoji), event triples, and the _determine_action
coordinator that decomposes the daily schedule into specific actions.
"""
from constant import debug
from persona.prompt_template.prompts.action import (
    run_gpt_prompt_action_sector,
    run_gpt_prompt_action_arena,
    run_gpt_prompt_action_game_object,
    run_gpt_prompt_pronunciatio,
    run_gpt_prompt_act_obj_desc,
    run_gpt_prompt_act_obj_event_triple,
)
from persona.prompt_template.prompts.reflection import run_gpt_prompt_event_triple
from persona.cognitive_modules.daily_planning import generate_task_decomp


def generate_action_sector(act_desp, persona, maze):
  """TODO
  Given the persona and the task description, choose the action_sector.

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT:
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT:
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT:
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_sector>")
  return run_gpt_prompt_action_sector(act_desp, persona, maze)[0]


def generate_action_arena(act_desp, persona, maze, act_world, act_sector):
  """TODO
  Given the persona and the task description, choose the action_arena.

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT:
    act_desp: description of the new action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT:
    action_arena (e.g., "bedroom 2")
  EXAMPLE OUTPUT:
    "bedroom 2"
  """
  if debug: print ("GNS FUNCTION: <generate_action_arena>")
  return run_gpt_prompt_action_arena(act_desp, persona, maze, act_world, act_sector)[0]


def generate_action_game_object(act_desp, act_address, persona, maze):
  """TODO
  Given the action description and the act address (the address where
  we expect the action to task place), choose one of the game objects.

  Persona state: identity stable set, n-1 day schedule, daily plan

  INPUT:
    act_desp: the description of the action (e.g., "sleeping")
    act_address: the arena where the action will take place:
               (e.g., "dolores double studio:double studio:bedroom 2")
    persona: The Persona class instance
  OUTPUT:
    act_game_object:
  EXAMPLE OUTPUT:
    "bed"
  """
  if debug: print ("GNS FUNCTION: <generate_action_game_object>")
  if not persona.s_mem.get_str_accessible_arena_game_objects(act_address):
    return "<random>"
  return run_gpt_prompt_action_game_object(act_desp, persona, maze, act_address)[0]


def generate_action_pronunciatio(act_desp, persona):
  """TODO
  Given an action description, creates an emoji string description via a few
  shot prompt.

  Does not really need any information from persona.

  INPUT:
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT:
    a string of emoji that translates action description.
  EXAMPLE OUTPUT:
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_pronunciatio>")
  try:
    x = run_gpt_prompt_pronunciatio(act_desp, persona)[0]
  except:
    x = "🙂"

  if not x:
    return "🙂"
  return x


def generate_action_event_triple(act_desp, persona):
  """TODO

  INPUT:
    act_desp: the description of the action (e.g., "sleeping")
    persona: The Persona class instance
  OUTPUT:
    a string of emoji that translates action description.
  EXAMPLE OUTPUT:
    "🧈🍞"
  """
  if debug: print ("GNS FUNCTION: <generate_action_event_triple>")
  return run_gpt_prompt_event_triple(act_desp, persona)[0]


def generate_act_obj_desc(act_game_object, act_desp, persona):
  if debug: print ("GNS FUNCTION: <generate_act_obj_desc>")
  ret = run_gpt_prompt_act_obj_desc(act_game_object, act_desp, persona)
  if ret is not None:
    return ret[0]
  else:
    return "is used"


def generate_act_obj_event_triple(act_game_object, act_obj_desc, persona):
  if debug: print ("GNS FUNCTION: <generate_act_obj_event_triple>")
  return run_gpt_prompt_act_obj_event_triple(act_game_object, act_obj_desc, persona)[0]


def _determine_action(persona, maze):
  """
  Creates the next action sequence for the persona.
  The main goal of this function is to run "add_new_action" on the persona's
  scratch space, which sets up all the action related variables for the next
  action.
  As a part of this, the persona may need to decompose its hourly schedule as
  needed.
  INPUT
    persona: Current <Persona> instance whose action we are determining.
    maze: Current <Maze> instance.
  """
  def determine_decomp(act_desp, act_dura):
    """
    Given an action description and its duration, we determine whether we need
    to decompose it. If the action is about the agent sleeping, we generally
    do not want to decompose it, so that's what we catch here.

    INPUT:
      act_desp: the description of the action (e.g., "sleeping")
      act_dura: the duration of the action in minutes.
    OUTPUT:
      a boolean. True if we need to decompose, False otherwise.
    """
    if "sleep" not in act_desp and "bed" not in act_desp:
      return True
    elif "sleeping" in act_desp or "asleep" in act_desp or "in bed" in act_desp:
      return False
    elif "sleep" in act_desp or "bed" in act_desp:
      if act_dura > 60:
        return False
    return True

  # The goal of this function is to get us the action associated with
  # <curr_index>. As a part of this, we may need to decompose some large
  # chunk actions.
  # Importantly, we try to decompose at least two hours worth of schedule at
  # any given point.
  curr_index = persona.scratch.get_f_daily_schedule_index()
  curr_index_60 = persona.scratch.get_f_daily_schedule_index(advance=60)

  # * Decompose *
  # During the first hour of the day, we need to decompose two hours
  # sequence. We do that here.
  if curr_index == 0:
    # This portion is invoked if it is the first hour of the day.
    act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]
    if act_dura >= 60:
      # We decompose if the next action is longer than an hour, and fits the
      # criteria described in determine_decomp.
      if determine_decomp(act_desp, act_dura):
        persona.scratch.f_daily_schedule[curr_index:curr_index+1] = (
                            generate_task_decomp(persona, act_desp, act_dura))
    if curr_index_60 + 1 < len(persona.scratch.f_daily_schedule):
      act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60+1]
      if act_dura >= 60:
        if determine_decomp(act_desp, act_dura):
          persona.scratch.f_daily_schedule[curr_index_60+1:curr_index_60+2] = (
                            generate_task_decomp(persona, act_desp, act_dura))

  if curr_index_60 < len(persona.scratch.f_daily_schedule):
    # If it is not the first hour of the day, this is always invoked (it is
    # also invoked during the first hour of the day -- to double up so we can
    # decompose two hours in one go). Of course, we need to have something to
    # decompose as well, so we check for that too.
    if persona.scratch.curr_time.hour < 23:
      # And we don't want to decompose after 11 pm.
      act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index_60]
      if act_dura >= 60:
        if determine_decomp(act_desp, act_dura):
          persona.scratch.f_daily_schedule[curr_index_60:curr_index_60+1] = (
                              generate_task_decomp(persona, act_desp, act_dura))
  # * End of Decompose *

  # Generate an <Action> instance from the action description and duration. By
  # this point, we assume that all the relevant actions are decomposed and
  # ready in f_daily_schedule.
  print ("DEBUG LJSDLFSKJF")
  for i in persona.scratch.f_daily_schedule: print (i)
  print (curr_index)
  print (len(persona.scratch.f_daily_schedule))
  print (persona.scratch.name)
  print ("------")

  # 1440
  x_emergency = 0
  for i in persona.scratch.f_daily_schedule:
    x_emergency += i[1]
  # print ("x_emergency", x_emergency)

  if 1440 - x_emergency > 0:
    print ("x_emergency__AAA", x_emergency)
  persona.scratch.f_daily_schedule += [["sleeping", 1440 - x_emergency]]

  act_desp, act_dura = persona.scratch.f_daily_schedule[curr_index]

  # Finding the target location of the action and creating action-related
  # variables.
  act_world = maze.access_tile(persona.scratch.curr_tile)["world"]
  # act_sector = maze.access_tile(persona.scratch.curr_tile)["sector"]
  act_sector = generate_action_sector(act_desp, persona, maze)
  act_arena = generate_action_arena(act_desp, persona, maze, act_world, act_sector)
  act_address = f"{act_world}:{act_sector}:{act_arena}"
  act_game_object = generate_action_game_object(act_desp, act_address,
                                                persona, maze)
  new_address = f"{act_world}:{act_sector}:{act_arena}:{act_game_object}"
  act_pron = generate_action_pronunciatio(act_desp, persona)
  act_event = generate_action_event_triple(act_desp, persona)
  # Persona's actions also influence the object states. We set those up here.
  act_obj_desp = generate_act_obj_desc(act_game_object, act_desp, persona)
  act_obj_pron = generate_action_pronunciatio(act_obj_desp, persona)
  act_obj_event = generate_act_obj_event_triple(act_game_object,
                                                act_obj_desp, persona)

  # Adding the action to persona's queue.
  persona.scratch.add_new_action(new_address,
                                 int(act_dura),
                                 act_desp,
                                 act_pron,
                                 act_event,
                                 None,
                                 None,
                                 None,
                                 None,
                                 act_obj_desp,
                                 act_obj_pron,
                                 act_obj_event)
