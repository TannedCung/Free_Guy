"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reaction_planning.py
Description: Reaction and conversation planning functions for generative agents.
Handles deciding whether to talk/react, conversation generation, choosing which
retrieved event to focus on, and the reaction coordinators (_should_react,
_create_react, _chat_react, _wait_react).
"""
from __future__ import annotations

import datetime
import math
import random
from typing import TYPE_CHECKING, Any, Optional, Union

if TYPE_CHECKING:
  from persona.persona import Persona
  from maze import Maze

from constant import debug
from persona.prompt_template.prompts.conversation import (
    run_gpt_prompt_summarize_conversation,
    run_gpt_prompt_decide_to_talk,
    run_gpt_prompt_decide_to_react,
)
from persona.cognitive_modules.daily_planning import generate_new_decomp_schedule
from persona.cognitive_modules.converse import agent_chat_v2


def generate_convo(maze: Maze, init_persona: Persona, target_persona: Persona) -> tuple[list[list[str]], int]:
  curr_loc = maze.access_tile(init_persona.scratch.curr_tile)  # type: ignore[arg-type]

  # convo = run_gpt_prompt_create_conversation(init_persona, target_persona, curr_loc)[0]
  # convo = agent_chat_v1(maze, init_persona, target_persona)
  convo = agent_chat_v2(maze, init_persona, target_persona)
  all_utt = ""

  for row in convo:
    speaker = row[0]
    utt = row[1]
    all_utt += f"{speaker}: {utt}\n"

  convo_length = math.ceil(int(len(all_utt)/8) / 30)

  if debug: print ("GNS FUNCTION: <generate_convo>")
  return convo, convo_length


def generate_convo_summary(persona: Persona, convo: list[list[str]]) -> str:
  convo_summary = run_gpt_prompt_summarize_conversation(persona, convo)[0]
  return convo_summary


def generate_decide_to_talk(init_persona: Persona, target_persona: Persona, retrieved: dict[str, Any]) -> bool:
  x = run_gpt_prompt_decide_to_talk(init_persona, target_persona, retrieved)[0]
  if debug: print ("GNS FUNCTION: <generate_decide_to_talk>")

  if x == "yes":
    return True
  else:
    return False


def generate_decide_to_react(init_persona: Persona, target_persona: Persona, retrieved: dict[str, Any]) -> str:
  if debug: print ("GNS FUNCTION: <generate_decide_to_react>")
  return run_gpt_prompt_decide_to_react(init_persona, target_persona, retrieved)[0]


def _choose_retrieved(persona: Persona, retrieved: dict[str, dict[str, Any]]) -> Optional[dict[str, Any]]:
  """
  Retrieved elements have multiple core "curr_events". We need to choose one
  event to which we are going to react to. We pick that event here.
  INPUT
    persona: Current <Persona> instance whose action we are determining.
    retrieved: A dictionary of <ConceptNode> that were retrieved from the
               the persona's associative memory. This dictionary takes the
               following form:
               dictionary[event.description] =
                 {["curr_event"] = <ConceptNode>,
                  ["events"] = [<ConceptNode>, ...],
                  ["thoughts"] = [<ConceptNode>, ...] }
  """
  # Once we are done with the reflection, we might want to build a more
  # complex structure here.

  # We do not want to take self events... for now
  copy_retrieved = retrieved.copy()
  for event_desc, rel_ctx in copy_retrieved.items():
    curr_event = rel_ctx["curr_event"]
    if curr_event.subject == persona.name:
      del retrieved[event_desc]

  # Always choose persona first.
  priority: list[dict[str, Any]] = []
  for event_desc, rel_ctx in retrieved.items():
    curr_event = rel_ctx["curr_event"]
    if (":" not in curr_event.subject
        and curr_event.subject != persona.name):
      priority += [rel_ctx]
  if priority:
    return random.choice(priority)

  # Skip idle.
  for event_desc, rel_ctx in retrieved.items():
    curr_event = rel_ctx["curr_event"]
    if "is idle" not in event_desc:
      priority += [rel_ctx]
  if priority:
    return random.choice(priority)
  return None


def _should_react(persona: Persona, retrieved: dict[str, Any], personas: dict[str, Persona]) -> Union[str, bool]:
  """
  Determines what form of reaction the persona should exihibit given the
  retrieved values.
  INPUT
    persona: Current <Persona> instance whose action we are determining.
    retrieved: A dictionary of <ConceptNode> that were retrieved from the
               the persona's associative memory. This dictionary takes the
               following form:
               dictionary[event.description] =
                 {["curr_event"] = <ConceptNode>,
                  ["events"] = [<ConceptNode>, ...],
                  ["thoughts"] = [<ConceptNode>, ...] }
    personas: A dictionary that contains all persona names as keys, and the
              <Persona> instance as values.
  """
  def lets_talk(init_persona: Persona, target_persona: Persona, retrieved: dict[str, Any]) -> bool:
    if (not target_persona.scratch.act_address
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description):
      return False

    if ("sleeping" in target_persona.scratch.act_description
        or "sleeping" in init_persona.scratch.act_description):
      return False

    if init_persona.scratch.curr_time.hour == 23:  # type: ignore[union-attr]
      return False

    if "<waiting>" in target_persona.scratch.act_address:
      return False

    if (target_persona.scratch.chatting_with
      or init_persona.scratch.chatting_with):
      return False

    if (target_persona.name in init_persona.scratch.chatting_with_buffer):
      if init_persona.scratch.chatting_with_buffer[target_persona.name] > 0:
        return False

    if generate_decide_to_talk(init_persona, target_persona, retrieved):

      return True

    return False

  def lets_react(init_persona: Persona, target_persona: Persona, retrieved: dict[str, Any]) -> Union[str, bool]:
    if (not target_persona.scratch.act_address
        or not target_persona.scratch.act_description
        or not init_persona.scratch.act_address
        or not init_persona.scratch.act_description):
      return False

    if ("sleeping" in target_persona.scratch.act_description
        or "sleeping" in init_persona.scratch.act_description):
      return False

    # return False
    if init_persona.scratch.curr_time.hour == 23:  # type: ignore[union-attr]
      return False

    if "waiting" in target_persona.scratch.act_description:
      return False
    if init_persona.scratch.planned_path == []:
      return False

    if (init_persona.scratch.act_address
        != target_persona.scratch.act_address):
      return False

    react_mode = generate_decide_to_react(init_persona,
                                          target_persona, retrieved)

    if react_mode == "1":
      wait_until = ((target_persona.scratch.act_start_time  # type: ignore[operator]
        + datetime.timedelta(minutes=target_persona.scratch.act_duration - 1))  # type: ignore[operator]
        .strftime("%B %d, %Y, %H:%M:%S"))  # type: ignore[union-attr]
      return f"wait: {wait_until}"
    elif react_mode == "2":
      return False
      return "do other things"
    else:
      return False #"keep"

  # If the persona is chatting right now, default to no reaction
  if persona.scratch.chatting_with:
    return False
  if "<waiting>" in persona.scratch.act_address:  # type: ignore[operator]
    return False

  # Recall that retrieved takes the following form:
  # dictionary {["curr_event"] = <ConceptNode>,
  #             ["events"] = [<ConceptNode>, ...],
  #             ["thoughts"] = [<ConceptNode>, ...]}
  curr_event = retrieved["curr_event"]

  if ":" not in curr_event.subject:
    # this is a persona event.
    if lets_talk(persona, personas[curr_event.subject], retrieved):
      return f"chat with {curr_event.subject}"
    react_mode = lets_react(persona, personas[curr_event.subject],
                            retrieved)
    return react_mode
  return False


def _create_react(persona: Persona, inserted_act: str, inserted_act_dur: int,
                  act_address: str, act_event: tuple[str, str, str],
                  chatting_with: Optional[str], chat: Optional[list[list[str]]],
                  chatting_with_buffer: Optional[dict[str, int]],
                  chatting_end_time: Optional[datetime.datetime],
                  act_pronunciatio: str, act_obj_description: Optional[str],
                  act_obj_pronunciatio: Optional[str],
                  act_obj_event: tuple[Optional[str], Optional[str], Optional[str]],
                  act_start_time: Optional[datetime.datetime] = None) -> None:
  p = persona

  min_sum = 0
  for i in range (p.scratch.get_f_daily_schedule_hourly_org_index()):
    min_sum += p.scratch.f_daily_schedule_hourly_org[i][1]
  start_hour = int (min_sum/60)

  if (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] >= 120):
    end_hour = start_hour + p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1]/60

  elif (p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
      p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()+1][1]):
    end_hour = start_hour + ((p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()][1] +
              p.scratch.f_daily_schedule_hourly_org[p.scratch.get_f_daily_schedule_hourly_org_index()+1][1])/60)

  else:
    end_hour = start_hour + 2
  end_hour = int(end_hour)

  dur_sum = 0
  count = 0
  start_index = None
  end_index = None
  for act, dur in p.scratch.f_daily_schedule:
    if dur_sum >= start_hour * 60 and start_index == None:
      start_index = count
    if dur_sum >= end_hour * 60 and end_index == None:
      end_index = count
    dur_sum += dur
    count += 1

  ret = generate_new_decomp_schedule(p, inserted_act, inserted_act_dur,
                                       start_hour, end_hour)
  p.scratch.f_daily_schedule[start_index:end_index] = ret
  p.scratch.add_new_action(act_address,
                           inserted_act_dur,
                           inserted_act,
                           act_pronunciatio,
                           act_event,
                           chatting_with,
                           chat,
                           chatting_with_buffer,
                           chatting_end_time,
                           act_obj_description,
                           act_obj_pronunciatio,
                           act_obj_event,
                           act_start_time)


def _chat_react(maze: Maze, persona: Persona, focused_event: dict[str, Any], reaction_mode: str, personas: dict[str, Persona]) -> None:
  # There are two personas -- the persona who is initiating the conversation
  # and the persona who is the target. We get the persona instances here.
  init_persona = persona
  target_persona = personas[reaction_mode[9:].strip()]
  curr_personas = [init_persona, target_persona]

  # Actually creating the conversation here.
  convo, duration_min = generate_convo(maze, init_persona, target_persona)
  convo_summary = generate_convo_summary(init_persona, convo)
  inserted_act = convo_summary
  inserted_act_dur = duration_min

  act_start_time = target_persona.scratch.act_start_time

  curr_time = target_persona.scratch.curr_time
  if curr_time.second != 0:  # type: ignore[union-attr]
    temp_curr_time = curr_time + datetime.timedelta(seconds=60 - curr_time.second)  # type: ignore[operator, union-attr]
    chatting_end_time = temp_curr_time + datetime.timedelta(minutes=inserted_act_dur)
  else:
    chatting_end_time = curr_time + datetime.timedelta(minutes=inserted_act_dur)  # type: ignore[operator]

  for role, p in [("init", init_persona), ("target", target_persona)]:
    if role == "init":
      act_address = f"<persona> {target_persona.name}"
      act_event = (p.name, "chat with", target_persona.name)
      chatting_with = target_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[target_persona.name] = 800
    elif role == "target":
      act_address = f"<persona> {init_persona.name}"
      act_event = (p.name, "chat with", init_persona.name)
      chatting_with = init_persona.name
      chatting_with_buffer = {}
      chatting_with_buffer[init_persona.name] = 800

    act_pronunciatio = "💬"
    act_obj_description = None
    act_obj_pronunciatio = None
    act_obj_event = (None, None, None)

    _create_react(p, inserted_act, inserted_act_dur,
      act_address, act_event, chatting_with, convo, chatting_with_buffer, chatting_end_time,  # type: ignore[arg-type]
      act_pronunciatio, act_obj_description, act_obj_pronunciatio,
      act_obj_event, act_start_time)


def _wait_react(persona: Persona, reaction_mode: str) -> None:
  p = persona

  inserted_act = f'waiting to start {p.scratch.act_description.split("(")[-1][:-1]}'  # type: ignore[union-attr]
  end_time = datetime.datetime.strptime(reaction_mode[6:].strip(), "%B %d, %Y, %H:%M:%S")
  inserted_act_dur = (end_time.minute + end_time.hour * 60) - (p.scratch.curr_time.minute + p.scratch.curr_time.hour * 60) + 1  # type: ignore[union-attr]

  act_address = f"<waiting> {p.scratch.curr_tile[0]} {p.scratch.curr_tile[1]}"  # type: ignore[index]
  act_event = (p.name, "waiting to start", p.scratch.act_description.split("(")[-1][:-1])  # type: ignore[union-attr]
  chatting_with = None
  chat = None
  chatting_with_buffer = None
  chatting_end_time = None

  act_pronunciatio = "⌛"
  act_obj_description = None
  act_obj_pronunciatio = None
  act_obj_event = (None, None, None)

  _create_react(p, inserted_act, inserted_act_dur,
    act_address, act_event, chatting_with, chat, chatting_with_buffer, chatting_end_time,
    act_pronunciatio, act_obj_description, act_obj_pronunciatio, act_obj_event)
