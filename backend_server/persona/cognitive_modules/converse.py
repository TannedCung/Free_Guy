"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: converse.py
Description: An extra cognitive module for generating conversations.
"""
from __future__ import annotations

import math
import datetime
import random
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
  from persona.persona import Persona
  from maze import Maze

from constant import debug
from persona.memory_structures.associative_memory import ConceptNode
from persona.cognitive_modules.retrieve import new_retrieve
from persona.prompt_template.llm_bridge import get_embedding
from persona.prompt_template.prompts.reflection import run_gpt_prompt_event_triple
from persona.prompt_template.prompts.perception import run_gpt_prompt_event_poignancy
from persona.prompt_template.prompts.conversation import (
    run_gpt_prompt_agent_chat_summarize_ideas,
    run_gpt_prompt_agent_chat_summarize_relationship,
    run_gpt_prompt_agent_chat,
    run_gpt_generate_iterative_chat_utt,
    run_gpt_generate_safety_score,
    run_gpt_prompt_summarize_ideas,
    run_gpt_prompt_generate_next_convo_line,
    run_gpt_prompt_generate_whisper_inner_thought,
    run_gpt_prompt_chat_poignancy,
)

def generate_agent_chat_summarize_ideas(init_persona: Persona,
                                        target_persona: Persona,
                                        retrieved: dict[str, list[ConceptNode]],
                                        curr_context: str) -> str:
  all_embedding_keys: list[str] = []
  for key, val in retrieved.items():
    for node in val:
      all_embedding_keys += [node.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  try: 
    summarized_idea = run_gpt_prompt_agent_chat_summarize_ideas(init_persona,
                        target_persona, all_embedding_key_str, 
                        curr_context)[0]
  except:
    summarized_idea = ""
  return summarized_idea


def generate_summarize_agent_relationship(init_persona: Persona,
                                          target_persona: Persona,
                                          retrieved: dict[str, list[ConceptNode]]) -> str:
  all_embedding_keys: list[str] = []
  for key, val in retrieved.items():
    for node in val:
      all_embedding_keys += [node.embedding_key]
  all_embedding_key_str =""
  for i in all_embedding_keys: 
    all_embedding_key_str += f"{i}\n"

  summarized_relationship = run_gpt_prompt_agent_chat_summarize_relationship(
                              init_persona, target_persona,
                              all_embedding_key_str)[0]
  return summarized_relationship


def generate_agent_chat(maze: Maze,
                        init_persona: Persona,
                        target_persona: Persona,
                        curr_context: str,
                        init_summ_idea: str,
                        target_summ_idea: str) -> list[list[str]]:
  summarized_idea = run_gpt_prompt_agent_chat(maze, 
                                              init_persona, 
                                              target_persona,
                                              curr_context, 
                                              init_summ_idea, 
                                              target_summ_idea)[0]
  for i in summarized_idea: 
    print (i)
  return summarized_idea


def agent_chat_v1(maze: Maze, init_persona: Persona, target_persona: Persona) -> list[list[str]]:
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is thinking of initating a conversation with " +
              f"{target_persona.scratch.name}.")

  summarized_ideas = []
  part_pairs = [(init_persona, target_persona), 
                (target_persona, init_persona)]
  for p_1, p_2 in part_pairs: 
    focal_points = [f"{p_2.scratch.name}"]
    retrieved = new_retrieve(p_1, focal_points, 50)
    relationship = generate_summarize_agent_relationship(p_1, p_2, retrieved)
    focal_points = [f"{relationship}", 
                    f"{p_2.scratch.name} is {p_2.scratch.act_description}"]
    retrieved = new_retrieve(p_1, focal_points, 25)
    summarized_idea = generate_agent_chat_summarize_ideas(p_1, p_2, retrieved, curr_context)
    summarized_ideas += [summarized_idea]

  return generate_agent_chat(maze, init_persona, target_persona, 
                      curr_context, 
                      summarized_ideas[0], 
                      summarized_ideas[1])


def generate_one_utterance(maze: Maze, init_persona: Persona, target_persona: Persona, retrieved: dict[str, list[ConceptNode]], curr_chat: list[list[str]]) -> tuple[str, bool]:
  # Chat version optimized for speed via batch generation
  curr_context = (f"{init_persona.scratch.name} " + 
              f"was {init_persona.scratch.act_description} " + 
              f"when {init_persona.scratch.name} " + 
              f"saw {target_persona.scratch.name} " + 
              f"in the middle of {target_persona.scratch.act_description}.\n")
  curr_context += (f"{init_persona.scratch.name} " +
              f"is initiating a conversation with " +
              f"{target_persona.scratch.name}.")

  print ("July 23 5")
  x = run_gpt_generate_iterative_chat_utt(maze, init_persona, target_persona, retrieved, curr_context, curr_chat)[0]

  print ("July 23 6")

  print ("adshfoa;khdf;fajslkfjald;sdfa HERE", x)

  return x["utterance"], x["end"]

def agent_chat_v2(maze: Maze, init_persona: Persona, target_persona: Persona) -> list[list[str]]:
  curr_chat: list[list[str]] = []
  print ("July 23")

  for _ in range(8):
    focal_points = [f"{target_persona.scratch.name}"]
    retrieved = new_retrieve(init_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(init_persona, target_persona, retrieved)
    print ("-------- relationshopadsjfhkalsdjf", relationship)
    last_chat = ""
    for row in curr_chat[-4:]:
      last_chat += ": ".join(row) + "\n"
    if last_chat:
      focal_points = [f"{relationship}",
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}",
                      last_chat]
    else:
      focal_points = [f"{relationship}",
                      f"{target_persona.scratch.name} is {target_persona.scratch.act_description}"]
    retrieved = new_retrieve(init_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, init_persona, target_persona, retrieved, curr_chat)

    curr_chat += [[init_persona.scratch.name, utt]]  # type: ignore[list-item]
    if end:
      break


    focal_points = [f"{init_persona.scratch.name}"]
    retrieved = new_retrieve(target_persona, focal_points, 50)
    relationship = generate_summarize_agent_relationship(target_persona, init_persona, retrieved)
    print ("-------- relationshopadsjfhkalsdjf", relationship)
    last_chat = ""
    for row in curr_chat[-4:]:
      last_chat += ": ".join(row) + "\n"
    if last_chat:
      focal_points = [f"{relationship}",
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}",
                      last_chat]
    else:
      focal_points = [f"{relationship}",
                      f"{init_persona.scratch.name} is {init_persona.scratch.act_description}"]
    retrieved = new_retrieve(target_persona, focal_points, 15)
    utt, end = generate_one_utterance(maze, target_persona, init_persona, retrieved, curr_chat)

    curr_chat += [[target_persona.scratch.name, utt]]  # type: ignore[list-item]
    if end:
      break

  print ("July 23 PU")
  for row in curr_chat: 
    print (row)
  print ("July 23 FIN")

  return curr_chat






def generate_summarize_ideas(persona: Persona, nodes: list[ConceptNode], question: str) -> str:
  statements = ""
  for n in nodes:
    statements += f"{n.embedding_key}\n"
  summarized_idea = run_gpt_prompt_summarize_ideas(persona, statements, question)[0]
  return summarized_idea


def generate_next_line(persona: Persona, interlocutor_desc: str, curr_convo: list[list[str]], summarized_idea: str) -> str:
  # Original chat -- line by line generation 
  prev_convo = ""
  for row in curr_convo: 
    prev_convo += f'{row[0]}: {row[1]}\n'

  next_line = run_gpt_prompt_generate_next_convo_line(persona, 
                                                      interlocutor_desc, 
                                                      prev_convo, 
                                                      summarized_idea)[0]  
  return next_line


def generate_inner_thought(persona: Persona, whisper: str) -> str:
  inner_thought = run_gpt_prompt_generate_whisper_inner_thought(persona, whisper)[0]
  return inner_thought

def generate_action_event_triple(act_desp: str, persona: Persona) -> tuple[str, str, str]:
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


def generate_poig_score(persona: Persona, event_type: str, description: str) -> Optional[int]:
  if debug: print ("GNS FUNCTION: <generate_poig_score>")

  if "is idle" in description: 
    return 1

  if event_type == "event" or event_type == "thought":
    return run_gpt_prompt_event_poignancy(persona, description)[0]
  elif event_type == "chat":
    return run_gpt_prompt_chat_poignancy(persona,
                           persona.scratch.act_description)[0]
  return None


def load_history_via_whisper(personas: dict[str, Persona], whispers: list[list[str]]) -> None:
  for count, row in enumerate(whispers): 
    persona = personas[row[0]]
    whisper = row[1]

    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)  # type: ignore[operator]
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o,  # type: ignore[arg-type]
                              thought, keywords, thought_poignancy,  # type: ignore[arg-type]
                              thought_embedding_pair, None)  # type: ignore[arg-type]


def open_convo_session(persona: Persona, convo_mode: str) -> None:
  if convo_mode == "analysis": 
    curr_convo = []
    interlocutor_desc = "Interviewer"

    while True: 
      line = input("Enter Input: ")
      if line == "end_convo": 
        break

      if int(run_gpt_generate_safety_score(persona, line)[0]) >= 8: 
        print (f"{persona.scratch.name} is a computational agent, and as such, it may be inappropriate to attribute human agency to the agent in your communication.")        

      else: 
        retrieved = new_retrieve(persona, [line], 50)[line]
        summarized_idea = generate_summarize_ideas(persona, retrieved, line)
        curr_convo += [[interlocutor_desc, line]]

        next_line = generate_next_line(persona, interlocutor_desc, curr_convo, summarized_idea)
        curr_convo += [[persona.scratch.name, next_line]]  # type: ignore[list-item]


  elif convo_mode == "whisper": 
    whisper = input("Enter Input: ")
    thought = generate_inner_thought(persona, whisper)

    created = persona.scratch.curr_time
    expiration = persona.scratch.curr_time + datetime.timedelta(days=30)  # type: ignore[operator]
    s, p, o = generate_action_event_triple(thought, persona)
    keywords = set([s, p, o])
    thought_poignancy = generate_poig_score(persona, "event", whisper)
    thought_embedding_pair = (thought, get_embedding(thought))
    persona.a_mem.add_thought(created, expiration, s, p, o,  # type: ignore[arg-type]
                              thought, keywords, thought_poignancy,  # type: ignore[arg-type]
                              thought_embedding_pair, None)  # type: ignore[arg-type]
































