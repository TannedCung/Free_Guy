"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: daily_planning.py
Description: Daily and hourly schedule planning functions for generative agents.
Handles long-term planning: wake-up hour, daily plan, hourly schedule, task
decomposition, identity revision, and the _long_term_planning coordinator.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
  from persona.persona import Persona

from constant import debug
from persona.prompt_template.llm_bridge import ChatGPT_single_request, get_embedding
from persona.prompt_template.prompts.planning import (
    run_gpt_prompt_wake_up_hour,
    run_gpt_prompt_daily_plan,
    run_gpt_prompt_generate_hourly_schedule,
    run_gpt_prompt_task_decomp,
    run_gpt_prompt_new_decomp_schedule,
)
from persona.cognitive_modules.retrieve import new_retrieve


def generate_wake_up_hour(persona: Persona) -> int:
  """
  Generates the time when the persona wakes up. This becomes an integral part
  of our process for generating the persona's daily plan.

  Persona state: identity stable set, lifestyle, first_name

  INPUT:
    persona: The Persona class instance
  OUTPUT:
    an integer signifying the persona's wake up hour
  EXAMPLE OUTPUT:
    8
  """
  if debug: print ("GNS FUNCTION: <generate_wake_up_hour>")
  return int(run_gpt_prompt_wake_up_hour(persona)[0])


def generate_first_daily_plan(persona: Persona, wake_up_hour: int) -> list[str]:
  """
  Generates the daily plan for the persona.
  Basically the long term planning that spans a day. Returns a list of actions
  that the persona will take today. Usually comes in the following form:
  'wake up and complete the morning routine at 6:00 am',
  'eat breakfast at 7:00 am',..
  Note that the actions come without a period.

  Persona state: identity stable set, lifestyle, cur_data_str, first_name

  INPUT:
    persona: The Persona class instance
    wake_up_hour: an integer that indicates when the hour the persona wakes up
                  (e.g., 8)
  OUTPUT:
    a list of daily actions in broad strokes.
  EXAMPLE OUTPUT:
    ['wake up and complete the morning routine at 6:00 am',
     'have breakfast and brush teeth at 6:30 am',
     'work on painting project from 8:00 am to 12:00 pm',
     'have lunch at 12:00 pm',
     'take a break and watch TV from 2:00 pm to 4:00 pm',
     'work on painting project from 4:00 pm to 6:00 pm',
     'have dinner at 6:00 pm', 'watch TV from 7:00 pm to 8:00 pm']
  """
  if debug: print ("GNS FUNCTION: <generate_first_daily_plan>")
  return run_gpt_prompt_daily_plan(persona, wake_up_hour)[0]


def generate_hourly_schedule(persona: Persona, wake_up_hour: int) -> list[list]:
  """
  Based on the daily req, creates an hourly schedule -- one hour at a time.
  The form of the action for each of the hour is something like below:
  "sleeping in her bed"

  The output is basically meant to finish the phrase, "x is..."

  Persona state: identity stable set, daily_plan

  INPUT:
    persona: The Persona class instance
    persona: Integer form of the wake up hour for the persona.
  OUTPUT:
    a list of activities and their duration in minutes:
  EXAMPLE OUTPUT:
    [['sleeping', 360], ['waking up and starting her morning routine', 60],
     ['eating breakfast', 60],..
  """
  if debug: print ("GNS FUNCTION: <generate_hourly_schedule>")

  hour_str = ["00:00 AM", "01:00 AM", "02:00 AM", "03:00 AM", "04:00 AM",
              "05:00 AM", "06:00 AM", "07:00 AM", "08:00 AM", "09:00 AM",
              "10:00 AM", "11:00 AM", "12:00 PM", "01:00 PM", "02:00 PM",
              "03:00 PM", "04:00 PM", "05:00 PM", "06:00 PM", "07:00 PM",
              "08:00 PM", "09:00 PM", "10:00 PM", "11:00 PM"]
  n_m1_activity: list[str] = []
  diversity_repeat_count = 3
  for _ in range(diversity_repeat_count):
    n_m1_activity_set = set(n_m1_activity)
    if len(n_m1_activity_set) < 5:
      n_m1_activity = []
      for count, curr_hour_str in enumerate(hour_str):
        if wake_up_hour > 0:
          n_m1_activity += ["sleeping"]
          wake_up_hour -= 1
        else:
          n_m1_activity += [run_gpt_prompt_generate_hourly_schedule(
                          persona, curr_hour_str, n_m1_activity, hour_str)[0]]

  # Step 1. Compressing the hourly schedule to the following format:
  # The integer indicates the number of hours. They should add up to 24.
  # [['sleeping', 6], ['waking up and starting her morning routine', 1],
  # ['eating breakfast', 1], ['getting ready for the day', 1],
  # ['working on her painting', 2], ['taking a break', 1],
  # ['having lunch', 1], ['working on her painting', 3],
  # ['taking a break', 2], ['working on her painting', 2],
  # ['relaxing and watching TV', 1], ['going to bed', 1], ['sleeping', 2]]
  _n_m1_hourly_compressed: list[list] = []
  prev: Optional[str] = None
  for act in n_m1_activity:
    if act != prev:
      _n_m1_hourly_compressed += [[act, 1]]
      prev = act
    else:
      if _n_m1_hourly_compressed:
        _n_m1_hourly_compressed[-1][1] += 1

  # Step 2. Expand to min scale (from hour scale)
  # [['sleeping', 360], ['waking up and starting her morning routine', 60],
  # ['eating breakfast', 60],..
  n_m1_hourly_compressed = []
  for task, duration in _n_m1_hourly_compressed:
    n_m1_hourly_compressed += [[task, duration*60]]

  return n_m1_hourly_compressed


def generate_task_decomp(persona: Persona, task: str, duration: int) -> list[list]:
  """
  A few shot decomposition of a task given the task description

  Persona state: identity stable set, curr_date_str, first_name

  INPUT:
    persona: The Persona class instance
    task: the description of the task at hand in str form
          (e.g., "waking up and starting her morning routine")
    duration: an integer that indicates the number of minutes this task is
              meant to last (e.g., 60)
  OUTPUT:
    a list of list where the inner list contains the decomposed task
    description and the number of minutes the task is supposed to last.
  EXAMPLE OUTPUT:
    [['going to the bathroom', 5], ['getting dressed', 5],
     ['eating breakfast', 15], ['checking her email', 5],
     ['getting her supplies ready for the day', 15],
     ['starting to work on her painting', 15]]

  """
  if debug: print ("GNS FUNCTION: <generate_task_decomp>")
  return run_gpt_prompt_task_decomp(persona, task, duration)[0]


def generate_new_decomp_schedule(persona: Persona, inserted_act: str, inserted_act_dur: int, start_hour: int, end_hour: int) -> list[list]:
  # Step 1: Setting up the core variables for the function.
  # <p> is the persona whose schedule we are editing right now.
  p = persona
  # <today_min_pass> indicates the number of minutes that have passed today.
  today_min_pass = (int(p.scratch.curr_time.hour) * 60  # type: ignore[union-attr]
                    + int(p.scratch.curr_time.minute) + 1)  # type: ignore[union-attr]

  # Step 2: We need to create <main_act_dur> and <truncated_act_dur>.
  # These are basically a sub-component of <f_daily_schedule> of the persona,
  # but focusing on the current decomposition.
  # Here is an example for <main_act_dur>:
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (uses the restroom)', 5]
  # ['wakes up and completes her morning routine (washes her ...)', 10]
  # ['wakes up and completes her morning routine (makes her bed)', 5]
  # ['wakes up and completes her morning routine (eats breakfast)', 15]
  # ['wakes up and completes her morning routine (gets dressed)', 10]
  # ['wakes up and completes her morning routine (leaves her ...)', 5]
  # ['wakes up and completes her morning routine (starts her ...)', 5]
  # ['preparing for her day (waking up at 6am)', 5]
  # ['preparing for her day (making her bed)', 5]
  # ['preparing for her day (taking a shower)', 15]
  # ['preparing for her day (getting dressed)', 5]
  # ['preparing for her day (eating breakfast)', 10]
  # ['preparing for her day (brushing her teeth)', 5]
  # ['preparing for her day (making coffee)', 5]
  # ['preparing for her day (checking her email)', 5]
  # ['preparing for her day (starting to work on her painting)', 5]
  #
  # And <truncated_act_dur> concerns only until where an event happens.
  # ['wakes up and completes her morning routine (wakes up at 6am)', 5]
  # ['wakes up and completes her morning routine (wakes up at 6am)', 2]
  main_act_dur = []
  truncated_act_dur = []
  dur_sum = 0 # duration sum
  count = 0 # enumerate count
  truncated_fin = False

  print ("DEBUG::: ", persona.scratch.name)
  for act, dur in p.scratch.f_daily_schedule:
    if (dur_sum >= start_hour * 60) and (dur_sum < end_hour * 60):
      main_act_dur += [[act, dur]]
      if dur_sum <= today_min_pass:
        truncated_act_dur += [[act, dur]]
      elif dur_sum > today_min_pass and not truncated_fin:
        # We need to insert that last act, duration list like this one:
        # e.g., ['wakes up and completes her morning routine (wakes up...)', 2]
        truncated_act_dur += [[p.scratch.f_daily_schedule[count][0],
                               dur_sum - today_min_pass]]
        truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass) ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
        # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass + 1) ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
        print ("DEBUG::: ", truncated_act_dur)

        # truncated_act_dur[-1][-1] -= (dur_sum - today_min_pass) ######## DEC 7 DEBUG;.. is the +1 the right thing to do???
        truncated_fin = True
    dur_sum += dur
    count += 1

  persona_name = persona.name
  main_act_dur = main_act_dur

  x = truncated_act_dur[-1][0].split("(")[0].strip() + " (on the way to " + truncated_act_dur[-1][0].split("(")[-1][:-1] + ")"
  truncated_act_dur[-1][0] = x

  if "(" in truncated_act_dur[-1][0]:
    inserted_act = truncated_act_dur[-1][0].split("(")[0].strip() + " (" + inserted_act + ")"

  # To do inserted_act_dur+1 below is an important decision but I'm not sure
  # if I understand the full extent of its implications. Might want to
  # revisit.
  truncated_act_dur += [[inserted_act, inserted_act_dur]]
  start_time_hour = (datetime.datetime(2022, 10, 31, 0, 0)
                   + datetime.timedelta(hours=start_hour))
  end_time_hour = (datetime.datetime(2022, 10, 31, 0, 0)
                   + datetime.timedelta(hours=end_hour))

  if debug: print ("GNS FUNCTION: <generate_new_decomp_schedule>")
  return run_gpt_prompt_new_decomp_schedule(persona,
                                            main_act_dur,
                                            truncated_act_dur,
                                            start_time_hour,
                                            end_time_hour,
                                            inserted_act,
                                            inserted_act_dur)[0]


def revise_identity(persona: Persona) -> None:
  p_name = persona.scratch.name

  focal_points = [f"{p_name}'s plan for {persona.scratch.get_str_curr_date_str()}.",
                  f"Important recent events for {p_name}'s life."]
  retrieved = new_retrieve(persona, focal_points)

  statements = "[Statements]\n"
  for key, val in retrieved.items():
    for i in val:
      statements += f"{i.created.strftime('%A %B %d -- %H:%M %p')}: {i.embedding_key}\n"

  # print (";adjhfno;asdjao;idfjo;af", p_name)
  plan_prompt = statements + "\n"
  plan_prompt += f"Given the statements above, is there anything that {p_name} should remember as they plan for"
  plan_prompt += f" *{persona.scratch.curr_time.strftime('%A %B %d')}*? "  # type: ignore[union-attr]
  plan_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement)\n\n"
  plan_prompt += f"Write the response from {p_name}'s perspective."
  plan_note = ChatGPT_single_request(plan_prompt)
  # print (plan_note)

  thought_prompt = statements + "\n"
  thought_prompt += f"Given the statements above, how might we summarize {p_name}'s feelings about their days up to now?\n\n"
  thought_prompt += f"Write the response from {p_name}'s perspective."
  thought_note = ChatGPT_single_request(thought_prompt)
  # print (thought_note)

  currently_prompt = f"{p_name}'s status from {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"  # type: ignore[operator, union-attr]
  currently_prompt += f"{persona.scratch.currently}\n\n"
  currently_prompt += f"{p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}:\n"  # type: ignore[operator, union-attr]
  currently_prompt += (plan_note + thought_note).replace('\n', '') + "\n\n"
  currently_prompt += f"It is now {persona.scratch.curr_time.strftime('%A %B %d')}. Given the above, write {p_name}'s status for {persona.scratch.curr_time.strftime('%A %B %d')} that reflects {p_name}'s thoughts at the end of {(persona.scratch.curr_time - datetime.timedelta(days=1)).strftime('%A %B %d')}. Write this in third-person talking about {p_name}."  # type: ignore[operator, union-attr]
  currently_prompt += f"If there is any scheduling information, be as specific as possible (include date, time, and location if stated in the statement).\n\n"
  currently_prompt += "Follow this format below:\nStatus: <new status>"
  # print ("DEBUG ;adjhfno;asdjao;asdfsidfjo;af", p_name)
  # print (currently_prompt)
  new_currently = ChatGPT_single_request(currently_prompt)
  # print (new_currently)
  # print (new_currently[10:])

  persona.scratch.currently = new_currently

  daily_req_prompt = persona.scratch.get_str_iss() + "\n"
  daily_req_prompt += f"Today is {persona.scratch.curr_time.strftime('%A %B %d')}. Here is {persona.scratch.name}'s plan today in broad-strokes (with the time of the day. e.g., have a lunch at 12:00 pm, watch TV from 7 to 8 pm).\n\n"  # type: ignore[union-attr]
  daily_req_prompt += f"Follow this format (the list should have 4~6 items but no more):\n"
  daily_req_prompt += f"1. wake up and complete the morning routine at <time>, 2. ..."

  new_daily_req = ChatGPT_single_request(daily_req_prompt)
  new_daily_req = new_daily_req.replace('\n', ' ')
  print ("WE ARE HERE!!!", new_daily_req)
  persona.scratch.daily_plan_req = new_daily_req


def _long_term_planning(persona: Persona, new_day: Union[str, bool]) -> None:
  """
  Formulates the persona's daily long-term plan if it is the start of a new
  day. This basically has two components: first, we create the wake-up hour,
  and second, we create the hourly schedule based on it.
  INPUT
    new_day: Indicates whether the current time signals a "First day",
             "New day", or False (for neither). This is important because we
             create the personas' long term planning on the new day.
  """
  # We start by creating the wake up hour for the persona.
  wake_up_hour = generate_wake_up_hour(persona)

  # When it is a new day, we start by creating the daily_req of the persona.
  # Note that the daily_req is a list of strings that describe the persona's
  # day in broad strokes.
  if new_day == "First day":
    # Bootstrapping the daily plan for the start of then generation:
    # if this is the start of generation (so there is no previous day's
    # daily requirement, or if we are on a new day, we want to create a new
    # set of daily requirements.
    persona.scratch.daily_req = generate_first_daily_plan(persona,
                                                          wake_up_hour)
  elif new_day == "New day":
    revise_identity(persona)

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - TODO
    # We need to create a new daily_req here...
    persona.scratch.daily_req = persona.scratch.daily_req

  # Based on the daily_req, we create an hourly schedule for the persona,
  # which is a list of todo items with a time duration (in minutes) that
  # add up to 24 hours.
  persona.scratch.f_daily_schedule = generate_hourly_schedule(persona,
                                                              wake_up_hour)
  persona.scratch.f_daily_schedule_hourly_org = (persona.scratch
                                                   .f_daily_schedule[:])


  # Added March 4 -- adding plan to the memory.
  thought = f"This is {persona.scratch.name}'s plan for {persona.scratch.curr_time.strftime('%A %B %d')}:"  # type: ignore[union-attr]
  for i in persona.scratch.daily_req:
    thought += f" {i},"
  thought = thought[:-1] + "."
  created = persona.scratch.curr_time
  expiration = persona.scratch.curr_time + datetime.timedelta(days=30)  # type: ignore[operator]
  s, p, o = (persona.scratch.name, "plan", persona.scratch.curr_time.strftime('%A %B %d'))  # type: ignore[union-attr]
  keywords = set(["plan"])
  thought_poignancy = 5
  thought_embedding_pair = (thought, get_embedding(thought))
  persona.a_mem.add_thought(created, expiration, s, p, o,  # type: ignore[arg-type]
                            thought, keywords, thought_poignancy,
                            thought_embedding_pair, None)  # type: ignore[arg-type]
