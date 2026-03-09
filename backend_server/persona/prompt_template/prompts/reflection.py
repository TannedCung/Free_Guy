"""
Reflection-related prompt functions for generative agents.

Functions that support higher-order thinking: generating focal points,
insights, event triples, thought poignancy, keyword extraction, and
knowledge synthesis from conversations.
"""
import re
import ast

from constant import debug
from persona.prompt_template.llm_bridge import (
    generate_prompt,
    safe_generate_response,
    ChatGPT_safe_generate_response,
)
from persona.prompt_template.print_prompt import print_run_prompts


def run_gpt_prompt_event_triple(action_description, persona, verbose=False):
  def create_prompt_input(action_description, persona):
    if "(" in action_description:
      action_description = action_description.split("(")[-1].split(")")[0]
    prompt_input = [persona.name,
                    action_description,
                    persona.name]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    cr = gpt_response.strip()
    cr = [i.strip() for i in cr.split(")")[0].split(",")]
    return cr

  def __func_validate(gpt_response, prompt=""):
    try:
      gpt_response = __func_clean_up(gpt_response, prompt="")
      if len(gpt_response) != 2:
        return False
    except:
      return False
    return True

  def get_fail_safe(persona):
    fs = (persona.name, "is", "idle")
    return fs

  gpt_param = {"engine": "gemma2", "max_tokens": 30,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": ["\n"]}
  prompt_template = "persona/prompt_template/v2/generate_event_triple_v1.txt"
  prompt_input = create_prompt_input(action_description, persona)
  prompt = generate_prompt(prompt_input, prompt_template)
  fail_safe = get_fail_safe(persona)  ########
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)
  output = (persona.name, output[0], output[1])

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_thought_poignancy(persona, event_description, test_input=None, verbose=False):
  def create_prompt_input(persona, event_description, test_input=None):
    prompt_input = [persona.scratch.name,
                    persona.scratch.get_str_iss(),
                    persona.scratch.name,
                    event_description]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    gpt_response = int(gpt_response.strip())
    return gpt_response

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe():
    return 4

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response, prompt=""):  ############
    gpt_response = int(gpt_response)
    return gpt_response

  def __chat_func_validate(gpt_response, prompt=""):  ############
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  print("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 8")  ########
  gpt_param = {"engine": "gemma2", "max_tokens": 15,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/poignancy_thought_v1.txt"  ########
  prompt_input = create_prompt_input(persona, event_description)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = "5"  ########
  special_instruction = "The output should ONLY contain ONE integer value on the scale of 1 to 10."  ########
  fail_safe = get_fail_safe()  ########
  output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
                                          __chat_func_validate, __chat_func_clean_up, True)
  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================


def run_gpt_prompt_focal_pt(persona, statements, n, test_input=None, verbose=False):
  def create_prompt_input(persona, statements, n, test_input=None):
    prompt_input = [statements, str(n)]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    gpt_response = "1) " + gpt_response.strip()
    ret = []
    for i in gpt_response.split("\n"):
      ret += [i.split(") ")[-1]]
    return ret

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe(n):
    return ["Who am I"] * n

  # ChatGPT Plugin ===========================================================
  def __chat_func_clean_up(gpt_response, prompt=""):  ############
    ret = ast.literal_eval(gpt_response)
    return ret

  def __chat_func_validate(gpt_response, prompt=""):  ############
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  print("asdhfapsh8p9hfaiafdsi;ldfj as DEBUG 12")  ########
  gpt_param = {"engine": "gemma2", "max_tokens": 15,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v3_ChatGPT/generate_focal_pt_v1.txt"  ########
  prompt_input = create_prompt_input(persona, statements, n)  ########
  prompt = generate_prompt(prompt_input, prompt_template)
  example_output = '["What should Jane do for lunch", "Does Jane like strawberry", "Who is Jane"]'  ########
  special_instruction = "Output must be a list of str."  ########
  fail_safe = get_fail_safe(n)  ########
  output = ChatGPT_safe_generate_response(prompt, example_output, special_instruction, 3, fail_safe,
                                          __chat_func_validate, __chat_func_clean_up, True)
  if output != False:
    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
  # ChatGPT Plugin ===========================================================

  gpt_param = {"engine": "gemma2", "max_tokens": 150,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/generate_focal_pt_v1.txt"
  prompt_input = create_prompt_input(persona, statements, n)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe(n)
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_insight_and_guidance(persona, statements, n, test_input=None, verbose=False):
  def create_prompt_input(persona, statements, n, test_input=None):
    prompt_input = [statements, str(n)]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    gpt_response = "1. " + gpt_response.strip()
    ret = dict()
    for i in gpt_response.split("\n"):
      row = i.split(". ")[-1]
      thought = row.split("(because of ")[0].strip()
      evi_raw = row.split("(because of ")[1].split(")")[0].strip()
      evi_raw = re.findall(r'\d+', evi_raw)
      evi_raw = [int(i.strip()) for i in evi_raw]
      ret[thought] = evi_raw
    return ret

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe(n):
    return ["I am hungry"] * n

  gpt_param = {"engine": "gemma2", "max_tokens": 150,
               "temperature": 0.5, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/insight_and_evidence_v1.txt"
  prompt_input = create_prompt_input(persona, statements, n)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe(n)
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_extract_keywords(persona, description, test_input=None, verbose=False):
  def create_prompt_input(description, test_input=None):
    if "\n" in description:
      description = description.replace("\n", " <LINE_BREAK> ")
    prompt_input = [description]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    print("???")
    print(gpt_response)
    gpt_response = gpt_response.strip().split("Emotive keywords:")
    factual = [i.strip() for i in gpt_response[0].split(",")]
    emotive = [i.strip() for i in gpt_response[1].split(",")]
    all_keywords = factual + emotive
    ret = []
    for i in all_keywords:
      if i:
        i = i.lower()
        if i[-1] == ".":
          i = i[:-1]
        ret += [i]
    print(ret)
    return set(ret)

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe():
    return []

  gpt_param = {"engine": "gemma2", "max_tokens": 4096,
               "temperature": 0, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/get_keywords_v1.txt"
  prompt_input = create_prompt_input(description, test_input)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_keyword_to_thoughts(persona, keyword, concept_summary, test_input=None, verbose=False):
  def create_prompt_input(persona, keyword, concept_summary, test_input=None):
    prompt_input = [keyword, concept_summary, persona.name]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    gpt_response = gpt_response.strip()
    return gpt_response

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe():
    return ""

  gpt_param = {"engine": "gemma2", "max_tokens": 40,
               "temperature": 0.7, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/keyword_to_thoughts_v1.txt"
  prompt_input = create_prompt_input(persona, keyword, concept_summary)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_convo_to_thoughts(persona,
                                     init_persona_name,
                                     target_persona_name,
                                     convo_str,
                                     fin_target, test_input=None, verbose=False):
  def create_prompt_input(init_persona_name,
                          target_persona_name,
                          convo_str,
                          fin_target, test_input=None):
    prompt_input = [init_persona_name,
                    target_persona_name,
                    convo_str,
                    init_persona_name,
                    fin_target]
    return prompt_input

  def __func_clean_up(gpt_response, prompt=""):
    gpt_response = gpt_response.strip()
    return gpt_response

  def __func_validate(gpt_response, prompt=""):
    try:
      __func_clean_up(gpt_response, prompt)
      return True
    except:
      return False

  def get_fail_safe():
    return ""

  gpt_param = {"engine": "gemma2", "max_tokens": 40,
               "temperature": 0.7, "top_p": 1, "stream": False,
               "frequency_penalty": 0, "presence_penalty": 0, "stop": None}
  prompt_template = "persona/prompt_template/v2/convo_to_thoughts_v1.txt"
  prompt_input = create_prompt_input(init_persona_name,
                                     target_persona_name,
                                     convo_str,
                                     fin_target)
  prompt = generate_prompt(prompt_input, prompt_template)

  fail_safe = get_fail_safe()
  output = safe_generate_response(prompt, gpt_param, 5, fail_safe,
                                   __func_validate, __func_clean_up)

  if debug or verbose:
    print_run_prompts(prompt_template, persona, gpt_param,
                      prompt_input, prompt, output)

  return output, [output, prompt, gpt_param, prompt_input, fail_safe]
