"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: run_gpt_prompt.py
Description: Re-export module. All prompt functions have been extracted to
submodules under persona/prompt_template/prompts/. This file exists for
backwards compatibility only.
"""

from persona.prompt_template.prompts.action import (
    run_gpt_prompt_act_obj_desc,
    run_gpt_prompt_act_obj_event_triple,
    run_gpt_prompt_action_arena,
    run_gpt_prompt_action_game_object,
    run_gpt_prompt_action_sector,
    run_gpt_prompt_pronunciatio,
)
from persona.prompt_template.prompts.conversation import (
    extract_first_json_dict,
    run_gpt_generate_iterative_chat_utt,
    run_gpt_generate_safety_score,
    run_gpt_prompt_agent_chat,
    run_gpt_prompt_agent_chat_summarize_ideas,
    run_gpt_prompt_agent_chat_summarize_relationship,
    run_gpt_prompt_chat_poignancy,
    run_gpt_prompt_create_conversation,
    run_gpt_prompt_decide_to_react,
    run_gpt_prompt_decide_to_talk,
    run_gpt_prompt_generate_next_convo_line,
    run_gpt_prompt_generate_whisper_inner_thought,
    run_gpt_prompt_memo_on_convo,
    run_gpt_prompt_planning_thought_on_convo,
    run_gpt_prompt_summarize_conversation,
    run_gpt_prompt_summarize_ideas,
)
from persona.prompt_template.prompts.perception import (
    run_gpt_prompt_event_poignancy,
)
from persona.prompt_template.prompts.planning import (
    run_gpt_prompt_daily_plan,
    run_gpt_prompt_generate_hourly_schedule,
    run_gpt_prompt_new_decomp_schedule,
    run_gpt_prompt_task_decomp,
    run_gpt_prompt_wake_up_hour,
)
from persona.prompt_template.prompts.reflection import (
    run_gpt_prompt_convo_to_thoughts,
    run_gpt_prompt_event_triple,
    run_gpt_prompt_extract_keywords,
    run_gpt_prompt_focal_pt,
    run_gpt_prompt_insight_and_guidance,
    run_gpt_prompt_keyword_to_thoughts,
    run_gpt_prompt_thought_poignancy,
)
from persona.prompt_template.prompts.utils import get_random_alphanumeric

__all__ = [
    "run_gpt_prompt_wake_up_hour",
    "run_gpt_prompt_daily_plan",
    "run_gpt_prompt_generate_hourly_schedule",
    "run_gpt_prompt_task_decomp",
    "run_gpt_prompt_new_decomp_schedule",
    "run_gpt_prompt_decide_to_talk",
    "run_gpt_prompt_decide_to_react",
    "run_gpt_prompt_create_conversation",
    "run_gpt_prompt_summarize_conversation",
    "run_gpt_prompt_chat_poignancy",
    "run_gpt_prompt_agent_chat_summarize_ideas",
    "run_gpt_prompt_agent_chat_summarize_relationship",
    "run_gpt_prompt_agent_chat",
    "run_gpt_prompt_summarize_ideas",
    "run_gpt_prompt_generate_next_convo_line",
    "run_gpt_prompt_generate_whisper_inner_thought",
    "run_gpt_prompt_planning_thought_on_convo",
    "run_gpt_prompt_memo_on_convo",
    "run_gpt_generate_safety_score",
    "extract_first_json_dict",
    "run_gpt_generate_iterative_chat_utt",
    "run_gpt_prompt_event_poignancy",
    "run_gpt_prompt_event_triple",
    "run_gpt_prompt_thought_poignancy",
    "run_gpt_prompt_focal_pt",
    "run_gpt_prompt_insight_and_guidance",
    "run_gpt_prompt_extract_keywords",
    "run_gpt_prompt_keyword_to_thoughts",
    "run_gpt_prompt_convo_to_thoughts",
    "run_gpt_prompt_action_sector",
    "run_gpt_prompt_action_arena",
    "run_gpt_prompt_action_game_object",
    "run_gpt_prompt_pronunciatio",
    "run_gpt_prompt_act_obj_desc",
    "run_gpt_prompt_act_obj_event_triple",
    "get_random_alphanumeric",
]
