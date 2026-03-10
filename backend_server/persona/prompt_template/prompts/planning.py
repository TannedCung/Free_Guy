"""
Planning-related prompt functions.

Contains prompts for daily plan generation, hourly schedule decomposition,
task breakdown, and schedule re-decomposition. Called from
persona/cognitive_modules/plan.py.
"""

import datetime

from constant import debug
from persona.prompt_template.llm_bridge import (
    generate_prompt,
    safe_generate_response,
)
from persona.prompt_template.print_prompt import print_run_prompts


def run_gpt_prompt_wake_up_hour(persona, test_input=None, verbose=False):
    """
    Given the persona, returns an integer that indicates the hour when the
    persona wakes up.

    INPUT:
      persona: The Persona class instance
    OUTPUT:
      integer for the wake up hour.
    """

    def create_prompt_input(persona, test_input=None):
        if test_input:
            return test_input
        prompt_input = [
            persona.scratch.get_str_iss(),
            persona.scratch.get_str_lifestyle(),
            persona.scratch.get_str_firstname(),
        ]
        return prompt_input

    def __func_clean_up(gpt_response, prompt=""):
        cr = int(gpt_response.strip().lower().split("am")[0])
        return cr

    def __func_validate(gpt_response, prompt=""):
        try:
            __func_clean_up(gpt_response, prompt="")
        except Exception:
            return False
        return True

    def get_fail_safe():
        fs = 8
        return fs

    gpt_param = {
        "engine": "gemma2",
        "max_tokens": 4096,
        "temperature": 0.8,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": ["\n"],
    }
    prompt_template = "persona/prompt_template/v2/wake_up_hour_v1.txt"
    prompt_input = create_prompt_input(persona, test_input)
    prompt = generate_prompt(prompt_input, prompt_template)
    fail_safe = get_fail_safe()

    output = safe_generate_response(prompt, gpt_param, 5, fail_safe, __func_validate, __func_clean_up)

    if debug or verbose:
        print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

    return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_daily_plan(persona, wake_up_hour, test_input=None, verbose=False):
    """
    Basically the long term planning that spans a day. Returns a list of actions
    that the persona will take today. Usually comes in the following form:
    'wake up and complete the morning routine at 6:00 am',
    'eat breakfast at 7:00 am',..
    Note that the actions come without a period.

    INPUT:
      persona: The Persona class instance
    OUTPUT:
      a list of daily actions in broad strokes.
    """

    def create_prompt_input(persona, wake_up_hour, test_input=None):
        if test_input:
            return test_input
        prompt_input = []
        prompt_input += [persona.scratch.get_str_iss()]
        prompt_input += [persona.scratch.get_str_lifestyle()]
        prompt_input += [persona.scratch.get_str_curr_date_str()]
        prompt_input += [persona.scratch.get_str_firstname()]
        prompt_input += [f"{str(wake_up_hour)}:00 am"]
        return prompt_input

    def __func_clean_up(gpt_response, prompt=""):
        cr = []
        _cr = gpt_response.split(")")
        for i in _cr:
            if i[-1].isdigit():
                i = i[:-1].strip()
                if len(i) > 0 and (i[-1] == "." or i[-1] == ","):  # End of the line
                    cr += [i[:-1].strip()]
        return cr

    def __func_validate(gpt_response, prompt=""):
        try:
            __func_clean_up(gpt_response, prompt="")
        except Exception:
            return False
        return True

    def get_fail_safe():
        fs = [
            "wake up and complete the morning routine at 6:00 am",
            "eat breakfast at 7:00 am",
            "read a book from 8:00 am to 12:00 pm",
            "have lunch at 12:00 pm",
            "take a nap from 1:00 pm to 4:00 pm",
            "relax and watch TV from 7:00 pm to 8:00 pm",
            "go to bed at 11:00 pm",
        ]
        return fs

    gpt_param = {
        "engine": "gemma2",
        "max_tokens": 500,
        "temperature": 1,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": None,
    }
    prompt_template = "persona/prompt_template/v2/daily_planning_v6.txt"
    prompt_input = create_prompt_input(persona, wake_up_hour, test_input)
    prompt = generate_prompt(prompt_input, prompt_template)
    fail_safe = get_fail_safe()

    output = safe_generate_response(prompt, gpt_param, 1, fail_safe, __func_validate, __func_clean_up)
    output = [f"wake up and complete the morning routine at {wake_up_hour}:00 am"] + output

    if debug or verbose:
        print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

    return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_generate_hourly_schedule(
    persona, curr_hour_str, p_f_ds_hourly_org, hour_str, intermission2=None, test_input=None, verbose=False
):
    def create_prompt_input(persona, curr_hour_str, p_f_ds_hourly_org, hour_str, intermission2=None, test_input=None):
        if test_input:
            return test_input
        schedule_format = ""
        schedule_format = schedule_format[:-1]

        intermission_str = "Here the originally intended hourly breakdown of"
        intermission_str += f" {persona.scratch.get_str_firstname()}'s schedule today: "
        for count, i in enumerate(persona.scratch.daily_req):
            intermission_str += f"{str(count + 1)}) {i}, "
        intermission_str = intermission_str[:-2]

        prior_schedule = ""
        if p_f_ds_hourly_org:
            prior_schedule = "\n"
            for count, i in enumerate(p_f_ds_hourly_org):
                prior_schedule = f"[{persona.scratch.get_str_curr_date_str()} --"
                prior_schedule += f" {hour_str[count]}] Activity:"
                prior_schedule += f" {persona.scratch.get_str_firstname()}"
                prior_schedule += f" is {i}\n"

        prompt_ending = f" By {persona.scratch.get_str_curr_date_str()}"
        prompt_ending += f" -- {curr_hour_str} "
        prompt_ending += f" {persona.scratch.get_str_firstname()} is"

        if intermission2:
            intermission2 = f"\n{intermission2}"

        prompt_input = []
        prompt_input += [schedule_format]
        prompt_input += [persona.scratch.get_str_iss()]

        prompt_input += [prior_schedule + "\n"]
        prompt_input += [intermission_str]
        if intermission2:
            prompt_input += [intermission2]
        else:
            prompt_input += [""]
        prompt_input += [prompt_ending]

        return prompt_input

    def __func_clean_up(gpt_response, prompt=""):
        cr = gpt_response.strip()
        if cr[-1] == ".":
            cr = cr[:-1]
        return cr

    def __func_validate(gpt_response, prompt=""):
        try:
            __func_clean_up(gpt_response, prompt="")
        except Exception:
            return False
        return True

    def get_fail_safe():
        fs = "asleep"
        return fs

    gpt_param = {
        "engine": "gemma2",
        "max_tokens": 4096,
        "temperature": 0.5,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": ["\n"],
    }
    prompt_template = "persona/prompt_template/v2/generate_hourly_schedule_v2.txt"
    prompt_input = create_prompt_input(persona, curr_hour_str, p_f_ds_hourly_org, hour_str, intermission2, test_input)
    prompt = generate_prompt(prompt_input, prompt_template)
    fail_safe = get_fail_safe()

    output = safe_generate_response(prompt, gpt_param, 2, fail_safe, __func_validate, __func_clean_up)

    if debug or verbose:
        print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

    return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_task_decomp(persona, task, duration, test_input=None, verbose=False):
    def create_prompt_input(persona, task, duration, test_input=None):
        """
        Today is Saturday June 25. From 00:00 ~ 06:00am, Maeve is
        planning on sleeping, 06:00 ~ 07:00am, Maeve is
        planning on waking up and doing her morning routine,
        and from 07:00am ~08:00am, Maeve is planning on having breakfast.
        """

        curr_f_org_index = persona.scratch.get_f_daily_schedule_hourly_org_index()
        all_indices = []
        all_indices += [curr_f_org_index]
        if curr_f_org_index + 1 <= len(persona.scratch.f_daily_schedule_hourly_org):
            all_indices += [curr_f_org_index + 1]
        if curr_f_org_index + 2 <= len(persona.scratch.f_daily_schedule_hourly_org):
            all_indices += [curr_f_org_index + 2]

        curr_time_range = ""

        print("DEBUG")
        print(persona.scratch.f_daily_schedule_hourly_org)
        print(all_indices)

        summ_str = f"Today is {persona.scratch.curr_time.strftime('%B %d, %Y')}. "
        summ_str += "From "
        for index in all_indices:
            print("index", index)
            if index < len(persona.scratch.f_daily_schedule_hourly_org):
                start_min = 0
                for i in range(index):
                    start_min += persona.scratch.f_daily_schedule_hourly_org[i][1]
                end_min = start_min + persona.scratch.f_daily_schedule_hourly_org[index][1]
                start_time = datetime.datetime.strptime("00:00:00", "%H:%M:%S") + datetime.timedelta(minutes=start_min)
                end_time = datetime.datetime.strptime("00:00:00", "%H:%M:%S") + datetime.timedelta(minutes=end_min)
                start_time_str = start_time.strftime("%H:%M%p")
                end_time_str = end_time.strftime("%H:%M%p")
                summ_str += f"{start_time_str} ~ {end_time_str}, {persona.name} is planning on {persona.scratch.f_daily_schedule_hourly_org[index][0]}, "
                if curr_f_org_index + 1 == index:
                    curr_time_range = f"{start_time_str} ~ {end_time_str}"
        summ_str = summ_str[:-2] + "."

        prompt_input = []
        prompt_input += [persona.scratch.get_str_iss()]
        prompt_input += [summ_str]
        prompt_input += [persona.scratch.get_str_firstname()]
        prompt_input += [persona.scratch.get_str_firstname()]
        prompt_input += [task]
        prompt_input += [curr_time_range]
        prompt_input += [duration]
        prompt_input += [persona.scratch.get_str_firstname()]
        return prompt_input

    def __func_clean_up(gpt_response, prompt=""):
        temp = [i.strip() for i in gpt_response.split("\n")]
        cr = []
        for count, i in enumerate(temp):
            if "duration:" not in i:
                continue  # skip the opening and ending of the response
            i = i.replace("**", "")
            k = [j.strip() for j in i.split("(duration:")]
            try:
                task_index = int(k[0].split(")")[0])
                task = k[0].replace(k[0].split(")")[0] + ") ", "")
            except Exception:
                task = k[0]
            if task[-1] == ".":
                task = task[:-1]
            try:
                duration = int(k[1].split(",")[0].split(" ")[0].replace(")", "").strip())
            except Exception as e:
                print(f"[ERROR]: parsing task decomp {e}")
                duration = 5
            cr += [[task, duration]]

        total_expected_min = int(prompt.split("(total duration in minutes")[-1].split(")")[0].strip())

        # TODO -- now, you need to make sure that this is the same as the sum of
        #         the current action sequence.
        curr_min_slot = []  # (task_name, task_index)
        for count, i in enumerate(cr):
            i_task = i[0]
            i_duration = i[1]

            # i_duration -= (i_duration % 5)
            if i_duration > 0:
                for j in range(i_duration):
                    curr_min_slot += [(i_task, count)]

        if len(curr_min_slot) > total_expected_min:
            curr_min_slot = curr_min_slot[:total_expected_min]
        elif len(curr_min_slot) < total_expected_min:
            last_task = curr_min_slot[-1]
            for i in range(total_expected_min - len(curr_min_slot)):
                curr_min_slot += [last_task]

        cr_ret = [
            ["dummy", -1],
        ]
        for task, task_index in curr_min_slot:
            if task != cr_ret[-1][0]:
                cr_ret += [[task, 1]]
            else:
                cr_ret[-1][1] += 1
        cr = cr_ret[1:]

        return cr

    def __func_validate(gpt_response, prompt=""):
        # TODO -- this sometimes generates error
        try:
            __func_clean_up(gpt_response, prompt=prompt)
        except Exception:
            # pass
            return False
        return gpt_response

    def get_fail_safe():
        fs = ["asleep"]
        return fs

    gpt_param = {
        "engine": "gemma2",
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": None,
    }
    prompt_template = "persona/prompt_template/v2/task_decomp_v3.txt"
    prompt_input = create_prompt_input(persona, task, duration)
    prompt = generate_prompt(prompt_input, prompt_template)
    fail_safe = get_fail_safe()

    print("?????")
    print(prompt)
    output = safe_generate_response(prompt, gpt_param, 3, get_fail_safe(), __func_validate, __func_clean_up)
    print(output)

    fin_output = []
    time_sum = 0
    for i_task, i_duration in output:
        time_sum += i_duration
        if time_sum <= duration:
            fin_output += [[i_task, i_duration]]
        else:
            break
    ftime_sum = 0
    for fi_task, fi_duration in fin_output:
        ftime_sum += fi_duration

    fin_output[-1][1] += duration - ftime_sum
    output = fin_output

    task_decomp = output
    ret = []
    for decomp_task, duration in task_decomp:
        ret += [[f"{task} ({decomp_task})", duration]]
    output = ret

    if debug or verbose:
        print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

    return output, [output, prompt, gpt_param, prompt_input, fail_safe]


def run_gpt_prompt_new_decomp_schedule(
    persona,
    main_act_dur,
    truncated_act_dur,
    start_time_hour,
    end_time_hour,
    inserted_act,
    inserted_act_dur,
    test_input=None,
    verbose=False,
):
    def create_prompt_input(
        persona,
        main_act_dur,
        truncated_act_dur,
        start_time_hour,
        end_time_hour,
        inserted_act,
        inserted_act_dur,
        test_input=None,
    ):
        persona_name = persona.name
        start_hour_str = start_time_hour.strftime("%H:%M %p")
        end_hour_str = end_time_hour.strftime("%H:%M %p")

        original_plan = ""
        for_time = start_time_hour
        for i in main_act_dur:
            original_plan += (
                f"{for_time.strftime('%H:%M')} ~ {(for_time + datetime.timedelta(minutes=int(i[1]))).strftime('%H:%M')} -- "
                + i[0]
            )
            original_plan += "\n"
            for_time += datetime.timedelta(minutes=int(i[1]))

        new_plan_init = ""
        for_time = start_time_hour
        for count, i in enumerate(truncated_act_dur):
            new_plan_init += (
                f"{for_time.strftime('%H:%M')} ~ {(for_time + datetime.timedelta(minutes=int(i[1]))).strftime('%H:%M')} -- "
                + i[0]
            )
            new_plan_init += "\n"
            if count < len(truncated_act_dur) - 1:
                for_time += datetime.timedelta(minutes=int(i[1]))

        new_plan_init += (for_time + datetime.timedelta(minutes=int(i[1]))).strftime("%H:%M") + " ~"

        prompt_input = [
            persona_name,
            start_hour_str,
            end_hour_str,
            original_plan,
            persona_name,
            inserted_act,
            inserted_act_dur,
            persona_name,
            start_hour_str,
            end_hour_str,
            end_hour_str,
            new_plan_init,
        ]
        return prompt_input

    def __func_clean_up(gpt_response, prompt=""):
        new_schedule = prompt + " " + gpt_response.strip()
        new_schedule = new_schedule.split("The revised schedule:")[-1].strip()
        new_schedule = new_schedule.split("\n")

        ret_temp = []
        for i in new_schedule:
            ret_temp += [i.split(" -- ")]

        ret = []
        for time_str, action in ret_temp:
            start_time = time_str.split(" ~ ")[0].strip()
            end_time = time_str.split(" ~ ")[1].strip()
            delta = datetime.datetime.strptime(end_time, "%H:%M") - datetime.datetime.strptime(start_time, "%H:%M")
            delta_min = int(delta.total_seconds() / 60)
            if delta_min < 0:
                delta_min = 0
            ret += [[action, delta_min]]

        return ret

    def __func_validate(gpt_response, prompt=""):
        try:
            gpt_response = __func_clean_up(gpt_response, prompt)
            dur_sum = 0
            for act, dur in gpt_response:
                dur_sum += dur
                if str(type(act)) != "<class 'str'>":
                    return False
                if str(type(dur)) != "<class 'int'>":
                    return False
            x = prompt.split("\n")[0].split("originally planned schedule from")[-1].strip()[:-1]
            x = [datetime.datetime.strptime(i.strip(), "%H:%M %p") for i in x.split(" to ")]
            delta_min = int((x[1] - x[0]).total_seconds() / 60)

            if int(dur_sum) != int(delta_min):
                return False

        except Exception:
            return False
        return True

    def get_fail_safe(main_act_dur, truncated_act_dur):
        dur_sum = 0
        for act, dur in main_act_dur:
            dur_sum += dur

        ret = truncated_act_dur[:]
        ret += main_act_dur[len(ret) - 1 :]

        # If there are access, we need to trim...
        ret_dur_sum = 0
        count = 0
        over = None
        for act, dur in ret:
            ret_dur_sum += dur
            if ret_dur_sum == dur_sum:
                break
            if ret_dur_sum > dur_sum:
                over = ret_dur_sum - dur_sum
                break
            count += 1

        if over:
            ret = ret[: count + 1]
            ret[-1][1] -= over

        return ret

    gpt_param = {
        "engine": "gemma2",
        "max_tokens": 1000,
        "temperature": 0,
        "top_p": 1,
        "stream": False,
        "frequency_penalty": 0,
        "presence_penalty": 0,
        "stop": None,
    }
    prompt_template = "persona/prompt_template/v2/new_decomp_schedule_v1.txt"
    prompt_input = create_prompt_input(
        persona,
        main_act_dur,
        truncated_act_dur,
        start_time_hour,
        end_time_hour,
        inserted_act,
        inserted_act_dur,
        test_input,
    )
    prompt = generate_prompt(prompt_input, prompt_template)
    fail_safe = get_fail_safe(main_act_dur, truncated_act_dur)
    output = safe_generate_response(prompt, gpt_param, 5, fail_safe, __func_validate, __func_clean_up)

    if debug or verbose:
        print_run_prompts(prompt_template, persona, gpt_param, prompt_input, prompt, output)

    return output, [output, prompt, gpt_param, prompt_input, fail_safe]
