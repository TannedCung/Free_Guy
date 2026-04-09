"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: reverie.py
Description: This is the main program for running generative agent simulations
that defines the ReverieServer class. This class maintains and records all
states related to the simulation. The primary mode of interaction for those
running the simulation should be through the open_server function, which
enables the simulator to input command-line prompts for running and saving
the simulation, among other tasks.

Release note (June 14, 2023) -- Reverie implements the core simulation
mechanism described in my paper entitled "Generative Agents: Interactive
Simulacra of Human Behavior." If you are reading through these lines after
having read the paper, you might notice that I use older terms to describe
generative agents and their cognitive modules here. Most notably, I use the
term "personas" to refer to generative agents, "associative memory" to refer
to the memory stream, and "reverie" to refer to the overarching simulation
framework.
"""

from __future__ import annotations

import datetime
import logging
import math
import time
import traceback
from typing import Any, Optional

from constant import maze_assets_loc
from db_persistence import (
    init_django,
    save_agent_memory,
    save_conversation,
    update_simulation_status,
    upsert_agent,
)
from global_methods import read_file_to_list
from maze import Maze
from persona.cognitive_modules.converse import load_history_via_whisper
from persona.persona import Persona
from utils.db_utils import get_runtime_state, set_runtime_state

logger = logging.getLogger(__name__)

##############################################################################
#                                  REVERIE                                   #
##############################################################################


class ReverieServer:
    fork_sim_code: str
    sim_code: str
    start_time: datetime.datetime
    curr_time: datetime.datetime
    sec_per_step: int
    maze: Maze
    step: int
    personas: dict[str, Persona]
    personas_tile: dict[str, tuple[int, int]]
    server_sleep: float
    # Optional DB objects (None when Django is not configured).
    _db_sim: Optional[Any]
    _db_agents: dict[str, Any]
    # Tracks how many memory nodes each persona had at the last DB sync, so we
    # only persist genuinely new nodes rather than re-saving everything.
    _db_memory_counts: dict[str, int]

    def __init__(self, fork_sim_code: str, sim_code: str) -> None:
        # FORKING FROM A PRIOR SIMULATION:
        # <fork_sim_code> indicates the simulation we are forking from.
        self.fork_sim_code = fork_sim_code
        self.sim_code = sim_code

        # Initialise Django ORM (required for all DB operations).
        init_django()

        # LOADING REVERIE'S GLOBAL VARIABLES FROM DATABASE
        try:
            from translator.models import EnvironmentState as EnvironmentStateModel
            from translator.models import Persona as PersonaModel
            from translator.models import Simulation as SimulationModel

            sim_db = SimulationModel.objects.get(name=sim_code)
        except Exception as exc:
            raise RuntimeError(f"Simulation '{sim_code}' not found in DB: {exc}") from exc

        self._db_sim: Optional[Any] = sim_db

        # Strip timezone from datetime fields (codebase uses naive datetimes).
        def _naive(dt: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
            if dt is None:
                return None
            return dt.replace(tzinfo=None) if dt.tzinfo else dt

        # <start_time> is the datetime instance for the start of the simulation.
        self.start_time = _naive(sim_db.start_date) or datetime.datetime.now()
        # <curr_time> is the game's current time, incremented each step.
        self.curr_time = _naive(sim_db.curr_time) or self.start_time
        # <sec_per_step> denotes seconds of in-game time per step.
        self.sec_per_step = sim_db.sec_per_step or 10
        # <maze> is the main Maze instance.
        self.maze = Maze(sim_db.maze_name or "")
        # <step> is the number of steps taken so far.
        self.step = sim_db.step

        # SETTING UP PERSONAS IN REVERIE
        self.personas: dict[str, Persona] = dict()
        self.personas_tile: dict[str, tuple[int, int]] = dict()

        # Load initial agent positions from EnvironmentState table.
        agent_positions: dict[str, Any] = {}
        try:
            env_state = EnvironmentStateModel.objects.get(simulation=sim_db, step=self.step)
            agent_positions = env_state.agent_positions or {}
        except EnvironmentStateModel.DoesNotExist:
            logger.warning("No EnvironmentState found for sim '%s' step %d", sim_code, self.step)

        # Load all active Persona objects from the database.
        persona_rows = PersonaModel.objects.filter(simulation=sim_db, status="active")
        for persona_row in persona_rows:
            curr_persona = Persona(persona_id=persona_row.pk)
            persona_name = curr_persona.name

            pos = agent_positions.get(persona_name, {})
            p_x = int(pos.get("x", 0))
            p_y = int(pos.get("y", 0))

            self.personas[persona_name] = curr_persona
            self.personas_tile[persona_name] = (p_x, p_y)
            self.maze.tiles[p_y][p_x]["events"].add(curr_persona.scratch.get_curr_event_and_desc())

        # REVERIE SETTINGS PARAMETERS:
        self.server_sleep = 0.01

        # Mark simulation as running.
        try:
            sim_db.status = "running"
            sim_db.save(update_fields=["status", "updated_at"])
        except Exception as exc:
            logger.warning("Could not update simulation status: %s", exc)

        # Legacy agent registry (retained for save_conversation / save_agent_memory calls).
        self._db_agents: dict[str, Any] = {}
        self._db_memory_counts: dict[str, int] = {}
        for persona_name, persona in self.personas.items():
            scratch = persona.scratch
            personality = " ".join(filter(None, [scratch.innate or "", scratch.learned or "", scratch.currently or ""]))
            db_agent = upsert_agent(
                self._db_sim,
                persona_name,
                personality_traits=personality,
                current_location=scratch.living_area or "",
                status="active",
            )
            if db_agent is not None:
                self._db_agents[persona_name] = db_agent
            self._db_memory_counts[persona_name] = len(persona.a_mem.id_to_node)

        # Signal the frontend about the current simulation.
        set_runtime_state("curr_sim_code", {"sim_code": self.sim_code})
        set_runtime_state("curr_step", {"step": self.step})

    def save(self) -> None:
        """
        Save all Reverie progress -- this includes Reverie's global state as well
        as all the personas.

        INPUT
          None
        OUTPUT
          None
          * Saves all relevant data to the PostgreSQL database
        """
        if self._db_sim is not None:
            try:
                from django.utils import timezone
                from translator.models import Simulation as SimulationModel

                curr_time_aware = (
                    timezone.make_aware(self.curr_time) if self.curr_time.tzinfo is None else self.curr_time
                )
                SimulationModel.objects.filter(pk=self._db_sim.pk).update(
                    curr_time=curr_time_aware,
                    step=self.step,
                    status="paused",
                )
            except Exception as exc:
                logger.warning("save: could not update Simulation row: %s", exc)
                update_simulation_status(self._db_sim, "paused")

        # Save all persona memory structures to DB (DB-mode save: no-arg calls).
        for persona_name, persona in self.personas.items():
            try:
                persona.save()
            except Exception as exc:
                logger.warning("save: could not save persona '%s': %s", persona_name, exc)

    def start_path_tester_server(self) -> None:
        """
        Starts the path tester server. This is for generating the spatial memory
        that we need for bootstrapping a persona's state.

        To use this, you need to open server and enter the path tester mode, and
        open the front-end side of the browser.

        INPUT
          None
        OUTPUT
          None
          * Saves the spatial memory of the test agent to the path_tester_env.json
            of the temp storage.
        """

        def print_tree(tree):
            def _print_tree(tree, depth):
                dash = " >" * depth

                if isinstance(tree, list):
                    if tree:
                        print(dash, tree)
                    return

                for key, val in tree.items():
                    if key:
                        print(dash, key)
                    _print_tree(val, depth + 1)

            _print_tree(tree, 0)

        # <curr_vision> is the vision radius of the test agent. Recommend 8 as
        # our default.
        curr_vision = 8
        # <s_mem> is our test spatial memory.
        s_mem: dict[str, Any] = dict()

        # The main while loop for the test agent.
        while True:
            try:
                curr_dict = {}
                tester_val = get_runtime_state("path_tester_env")
                if tester_val:
                    curr_dict = tester_val
                    set_runtime_state("path_tester_env", None)

                    # Current camera location
                    curr_sts = self.maze.sq_tile_size
                    curr_camera = (
                        int(math.ceil(curr_dict["x"] / curr_sts)),
                        int(math.ceil(curr_dict["y"] / curr_sts)) + 1,
                    )
                    curr_tile_det = self.maze.access_tile(curr_camera)

                    # Initiating the s_mem
                    world = curr_tile_det["world"]
                    if curr_tile_det["world"] not in s_mem:
                        s_mem[world] = dict()

                    # Iterating throughn the nearby tiles.
                    nearby_tiles = self.maze.get_nearby_tiles(curr_camera, curr_vision)
                    for i in nearby_tiles:
                        i_det = self.maze.access_tile(i)
                        if curr_tile_det["sector"] == i_det["sector"] and curr_tile_det["arena"] == i_det["arena"]:
                            if i_det["sector"] != "":
                                if i_det["sector"] not in s_mem[world]:
                                    s_mem[world][i_det["sector"]] = dict()
                            if i_det["arena"] != "":
                                if i_det["arena"] not in s_mem[world][i_det["sector"]]:
                                    s_mem[world][i_det["sector"]][i_det["arena"]] = list()
                            if i_det["game_object"] != "":
                                if i_det["game_object"] not in s_mem[world][i_det["sector"]][i_det["arena"]]:
                                    s_mem[world][i_det["sector"]][i_det["arena"]] += [i_det["game_object"]]

                # Incrementally outputting the s_mem and persisting to DB.
                print("= " * 15)
                set_runtime_state("path_tester_out", s_mem)
                print_tree(s_mem)

            except Exception:
                logger.debug("path_tester_server: error processing tile, continuing", exc_info=True)

            time.sleep(self.server_sleep * 10)

    def start_server(self, int_counter: int) -> None:
        """
        The main backend server of Reverie.
        This function retrieves the environment file from the frontend to
        understand the state of the world, calls on each personas to make
        decisions based on the world state, and saves their moves at certain step
        intervals.
        INPUT
          int_counter: Integer value for the number of steps left for us to take
                       in this iteration.
        OUTPUT
          None
        """
        # When a persona arrives at a game object, we give a unique event
        # to that object.
        # e.g., ('double studio[...]:bed', 'is', 'unmade', 'unmade')
        # Later on, before this cycle ends, we need to return that to its
        # initial state, like this:
        # e.g., ('double studio[...]:bed', None, None, None)
        # So we need to keep track of which event we added.
        # <game_obj_cleanup> is used for that.
        game_obj_cleanup: dict[tuple[Any, ...], tuple[int, int]] = dict()

        # The main while loop of Reverie.
        while True:
            # Done with this iteration if <int_counter> reaches 0.
            if int_counter == 0:
                break

            # Read the current environment state from the EnvironmentState table.
            # The frontend writes agent positions there; we wait until the row exists.
            new_env: dict[str, Any] = {}
            env_retrieved = False
            try:
                from translator.models import EnvironmentState as EnvironmentStateModel

                env_row = EnvironmentStateModel.objects.filter(simulation=self._db_sim, step=self.step).first()
                if env_row is None:
                    time.sleep(0.5)
                    continue
                new_env = env_row.agent_positions or {}
                env_retrieved = True
            except Exception:
                logger.warning("start_server: failed to read EnvironmentState for step %d", self.step, exc_info=True)

            if env_retrieved:
                # This is where we go through <game_obj_cleanup> to clean up all
                # object actions that were used in this cylce.
                for key, val in game_obj_cleanup.items():
                    # We turn all object actions to their blank form (with None).
                    self.maze.turn_event_from_tile_idle(key, val)
                # Then we initialize game_obj_cleanup for this cycle.
                game_obj_cleanup = dict()

                # We first move our personas in the backend environment to match
                # the frontend environment.
                for persona_name, persona in self.personas.items():
                    # <curr_tile> is the tile that the persona was at previously.
                    curr_tile = self.personas_tile[persona_name]
                    # <new_tile> is the tile that the persona will move to right now,
                    # during this cycle.
                    new_tile = (new_env[persona_name]["x"], new_env[persona_name]["y"])

                    # We actually move the persona on the backend tile map here.
                    self.personas_tile[persona_name] = new_tile
                    self.maze.remove_subject_events_from_tile(persona.name, curr_tile)
                    self.maze.add_event_from_tile(persona.scratch.get_curr_event_and_desc(), new_tile)

                    # Now, the persona will travel to get to their destination. *Once*
                    # the persona gets there, we activate the object action.
                    if not persona.scratch.planned_path:
                        # We add that new object action event to the backend tile map.
                        # At its creation, it is stored in the persona's backend.
                        game_obj_cleanup[persona.scratch.get_curr_obj_event_and_desc()] = new_tile
                        self.maze.add_event_from_tile(persona.scratch.get_curr_obj_event_and_desc(), new_tile)
                        # We also need to remove the temporary blank action for the
                        # object that is currently taking the action.
                        blank = (persona.scratch.get_curr_obj_event_and_desc()[0], None, None, None)
                        self.maze.remove_event_from_tile(blank, new_tile)

                # Then we need to actually have each of the personas perceive and
                # move. The movement for each of the personas comes in the form of
                # x y coordinates where the persona will move towards. e.g., (50, 34)
                # This is where the core brains of the personas are invoked.
                movements: dict[str, Any] = {"persona": dict(), "meta": dict()}
                for persona_name, persona in self.personas.items():
                    # <next_tile> is a x,y coordinate. e.g., (58, 9)
                    # <pronunciatio> is an emoji. e.g., "\ud83d\udca4"
                    # <description> is a string description of the movement. e.g.,
                    #   writing her next novel (editing her novel)
                    #   @ double studio:double studio:common room:sofa
                    next_tile, pronunciatio, description = persona.move(
                        self.maze, self.personas, self.personas_tile[persona_name], self.curr_time
                    )
                    movements["persona"][persona_name] = {}
                    movements["persona"][persona_name]["movement"] = next_tile
                    movements["persona"][persona_name]["pronunciatio"] = pronunciatio
                    movements["persona"][persona_name]["description"] = description
                    movements["persona"][persona_name]["chat"] = persona.scratch.chat

                # Include the meta information about the current stage in the
                # movements dictionary.
                movements["meta"]["curr_time"] = self.curr_time.strftime("%B %d, %Y, %H:%M:%S")

                # Compute next step/time before entering the transaction so that
                # self.step and self.curr_time are only updated after a successful commit.
                next_step = self.step + 1
                next_time = self.curr_time + datetime.timedelta(seconds=self.sec_per_step)

                # Wrap all DB writes for this step in a single atomic transaction.
                # This ensures the step is fully committed or fully rolled back.
                step_committed = False
                try:
                    from django.db import transaction
                    from django.utils import timezone
                    from translator.models import MovementRecord as MovementRecordModel
                    from translator.models import Simulation as SimulationModel

                    curr_time_aware = (
                        timezone.make_aware(self.curr_time) if self.curr_time.tzinfo is None else self.curr_time
                    )
                    next_time_aware = timezone.make_aware(next_time) if next_time.tzinfo is None else next_time
                    with transaction.atomic():
                        # Write persona movements to the MovementRecord table.
                        # The frontend reads from there to animate the simulation.
                        # Example movements dict:
                        # {"persona": {"Maria Lopez": {"movement": [58, 9]}},
                        #  "meta": {"curr_time": "..."}}
                        MovementRecordModel.objects.update_or_create(
                            simulation=self._db_sim,
                            step=self.step,
                            defaults={
                                "sim_curr_time": curr_time_aware,
                                "persona_movements": movements,
                            },
                        )

                        # -----------------------------------------------------------
                        # DATABASE PERSISTENCE: agent state + conversations
                        # -----------------------------------------------------------

                        for persona_name, persona in self.personas.items():
                            db_agent = self._db_agents.get(persona_name)
                            scratch = persona.scratch
                            # Update agent location and status in the DB.
                            new_location = scratch.act_address or scratch.living_area or ""
                            new_status = (
                                "sleeping"
                                if scratch.act_description and "sleeping" in (scratch.act_description or "").lower()
                                else "active"
                            )
                            db_agent = upsert_agent(
                                self._db_sim,
                                persona_name,
                                current_location=new_location,
                                status=new_status,
                            )
                            if db_agent is not None:
                                self._db_agents[persona_name] = db_agent

                            # Persist any active conversation.
                            if scratch.chat and scratch.chatting_with:
                                partner_agent = self._db_agents.get(scratch.chatting_with)
                                participants = [a for a in [db_agent, partner_agent] if a is not None]
                                save_conversation(
                                    self._db_sim,
                                    agent_objs=participants,
                                    started_at=self.curr_time,
                                    transcript=scratch.chat,
                                )

                            # Persist any new memory nodes created during this step.
                            prev_count = self._db_memory_counts.get(persona_name, 0)
                            all_nodes = list(persona.a_mem.id_to_node.values())
                            new_nodes = all_nodes[prev_count:]
                            for node in new_nodes:
                                save_agent_memory(
                                    db_agent,
                                    memory_type=node.type,
                                    content=node.description,
                                    importance_score=float(node.poignancy),
                                )
                            self._db_memory_counts[persona_name] = len(all_nodes)

                        # Persist updated step and curr_time to the Simulation row.
                        if self._db_sim is not None:
                            SimulationModel.objects.filter(pk=self._db_sim.pk).update(
                                step=next_step,
                                curr_time=next_time_aware,
                                status="running",
                            )

                        # Signal the frontend about the new step.
                        set_runtime_state("curr_sim_code", {"sim_code": self.sim_code})
                        set_runtime_state("curr_step", {"step": next_step})

                    step_committed = True

                except Exception:
                    logger.warning(
                        "start_server: transaction failed for step %d, rolling back",
                        self.step,
                        exc_info=True,
                    )

                # After this cycle, the world takes one step forward only if the
                # DB transaction committed successfully.
                if step_committed:
                    self.step = next_step
                    self.curr_time = next_time

                int_counter -= 1

            # Sleep so we don't burn our machines.
            time.sleep(self.server_sleep)

    def open_server(self) -> None:
        """
        Open up an interactive terminal prompt that lets you run the simulation
        step by step and probe agent state.

        INPUT
          None
        OUTPUT
          None
        """
        print("Note: The agents in this simulation package are computational")
        print("constructs powered by generative agents architecture and LLM. We")
        print("clarify that these agents lack human-like agency, consciousness,")
        print("and independent decision-making.\n---")

        while True:
            sim_command = input("Enter option: ")
            sim_command = sim_command.strip()
            ret_str = ""

            try:
                if sim_command.lower() in ["f", "fin", "finish", "save and finish"]:
                    # Finishes the simulation environment and saves the progress.
                    # Example: fin
                    self.save()
                    break

                elif sim_command.lower() == "start path tester mode":
                    # Starts the path tester server for spatial memory bootstrapping.
                    # Note that once you start this mode, you need to exit out of the
                    # session and restart in case you want to run something else.
                    self.start_path_tester_server()

                elif sim_command.lower() == "exit":
                    # Exits the simulation without saving.
                    # Example: exit
                    break

                elif sim_command.lower() == "save":
                    # Saves the current simulation progress.
                    # Example: save
                    self.save()

                elif sim_command[:3].lower() == "run":
                    # Runs the number of steps specified in the prompt.
                    # Example: run 1000
                    int_count = int(sim_command.split()[-1])
                    rs.start_server(int_count)

                elif "print persona schedule" in sim_command[:22].lower():
                    # Print the decomposed schedule of the persona specified in the
                    # prompt.
                    # Example: print persona schedule Isabella Rodriguez
                    ret_str += self.personas[
                        " ".join(sim_command.split()[-2:])
                    ].scratch.get_str_daily_schedule_summary()

                elif "print all persona schedule" in sim_command[:26].lower():
                    # Print the decomposed schedule of all personas in the world.
                    # Example: print all persona schedule
                    for persona_name, persona in self.personas.items():
                        ret_str += f"{persona_name}\n"
                        ret_str += f"{persona.scratch.get_str_daily_schedule_summary()}\n"
                        ret_str += "---\n"

                elif "print hourly org persona schedule" in sim_command.lower():
                    # Print the hourly schedule of the persona specified in the prompt.
                    # This one shows the original, non-decomposed version of the
                    # schedule.
                    # Ex: print persona schedule Isabella Rodriguez
                    ret_str += self.personas[
                        " ".join(sim_command.split()[-2:])
                    ].scratch.get_str_daily_schedule_hourly_org_summary()

                elif "print persona current tile" in sim_command[:26].lower():
                    # Print the x y tile coordinate of the persona specified in the
                    # prompt.
                    # Ex: print persona current tile Isabella Rodriguez
                    ret_str += str(self.personas[" ".join(sim_command.split()[-2:])].scratch.curr_tile)

                elif "print persona chatting with buffer" in sim_command.lower():
                    # Print the chatting with buffer of the persona specified in the
                    # prompt.
                    # Ex: print persona chatting with buffer Isabella Rodriguez
                    curr_persona = self.personas[" ".join(sim_command.split()[-2:])]
                    for p_n, count in curr_persona.scratch.chatting_with_buffer.items():
                        ret_str += f"{p_n}: {count}"

                elif "print persona associative memory (event)" in sim_command.lower():
                    # Print the associative memory (event) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (event) Isabella Rodriguez
                    ret_str += f"{self.personas[' '.join(sim_command.split()[-2:])]}\n"
                    ret_str += self.personas[" ".join(sim_command.split()[-2:])].a_mem.get_str_seq_events()

                elif "print persona associative memory (thought)" in sim_command.lower():
                    # Print the associative memory (thought) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (thought) Isabella Rodriguez
                    ret_str += f"{self.personas[' '.join(sim_command.split()[-2:])]}\n"
                    ret_str += self.personas[" ".join(sim_command.split()[-2:])].a_mem.get_str_seq_thoughts()

                elif "print persona associative memory (chat)" in sim_command.lower():
                    # Print the associative memory (chat) of the persona specified in
                    # the prompt
                    # Ex: print persona associative memory (chat) Isabella Rodriguez
                    ret_str += f"{self.personas[' '.join(sim_command.split()[-2:])]}\n"
                    ret_str += self.personas[" ".join(sim_command.split()[-2:])].a_mem.get_str_seq_chats()

                elif "print persona spatial memory" in sim_command.lower():
                    # Print the spatial memory of the persona specified in the prompt
                    # Ex: print persona spatial memory Isabella Rodriguez
                    self.personas[" ".join(sim_command.split()[-2:])].s_mem.print_tree()

                elif "print current time" in sim_command[:18].lower():
                    # Print the current time of the world.
                    # Ex: print current time
                    ret_str += f"{self.curr_time.strftime('%B %d, %Y, %H:%M:%S')}\n"
                    ret_str += f"steps: {self.step}"

                elif "print tile event" in sim_command[:16].lower():
                    # Print the tile events in the tile specified in the prompt
                    # Ex: print tile event 50, 30
                    cooordinate = tuple(int(i.strip()) for i in sim_command[16:].split(","))
                    for i in self.maze.access_tile(cooordinate)["events"]:  # type: ignore[arg-type]
                        ret_str += f"{i}\n"

                elif "print tile details" in sim_command.lower():
                    # Print the tile details of the tile specified in the prompt
                    # Ex: print tile event 50, 30
                    cooordinate = tuple(int(i.strip()) for i in sim_command[18:].split(","))
                    for key, val in self.maze.access_tile(cooordinate).items():  # type: ignore[arg-type]
                        ret_str += f"{key}: {val}\n"

                elif "call -- analysis" in sim_command.lower():
                    # Starts a stateless chat session with the agent. It does not save
                    # anything to the agent's memory.
                    # Ex: call -- analysis Isabella Rodriguez
                    persona_name = sim_command[len("call -- analysis") :].strip()
                    self.personas[persona_name].open_convo_session("analysis")

                elif "call -- load history" in sim_command.lower():
                    curr_file = maze_assets_loc + "/" + sim_command[len("call -- load history") :].strip()
                    # call -- load history the_ville/agent_history_init_n3.csv

                    rows = read_file_to_list(curr_file, header=True, strip_trail=True)[1]
                    clean_whispers = []
                    for row in rows:
                        agent_name = row[0].strip()
                        whispers = row[1].split(";")
                        whispers = [whisper.strip() for whisper in whispers]
                        for whisper in whispers:
                            clean_whispers += [[agent_name, whisper]]

                    load_history_via_whisper(self.personas, clean_whispers)

                print(ret_str)

            except Exception:
                traceback.print_exc()
                logger.error("open_server: command '%s' raised an error", sim_command, exc_info=True)
                print("Error.")


    # -----------------------------------------------------------------------
    # Stateless stage methods — for Vercel serverless step execution
    # -----------------------------------------------------------------------
    # Each method loads ReverieServer state from DB, runs one cognitive stage
    # for all personas, persists intermediate results to SimulationStepCache,
    # and returns a JSON-serializable result dict.
    #
    # Execution order per step:
    #   run_perceive → run_retrieve → run_plan → run_reflect → run_execute
    # -----------------------------------------------------------------------

    @classmethod
    def _load_for_stage(cls, sim_code: str) -> "ReverieServer":
        """Load a ReverieServer from DB without starting the polling loop.

        Reconstructs personas_tile from PersonaScratch.curr_tile and restores
        maze tile events from the saved game_obj_cleanup list.
        """
        init_django()

        from translator.models import EnvironmentState as EnvironmentStateModel  # noqa: PLC0415
        from translator.models import Persona as PersonaModel  # noqa: PLC0415
        from translator.models import Simulation as SimulationModel  # noqa: PLC0415

        try:
            sim_db = SimulationModel.objects.get(name=sim_code)
        except Exception as exc:
            raise RuntimeError(f"Simulation '{sim_code}' not found in DB: {exc}") from exc

        server: "ReverieServer" = cls.__new__(cls)
        server.fork_sim_code = sim_code
        server.sim_code = sim_code
        server._db_sim = sim_db
        server._db_agents = {}
        server._db_memory_counts = {}
        server.server_sleep = 1.0

        def _naive(dt: Optional[Any]) -> Optional[datetime.datetime]:
            if dt is None:
                return None
            return dt.replace(tzinfo=None) if getattr(dt, "tzinfo", None) else dt

        server.start_time = _naive(sim_db.start_date) or datetime.datetime.now()
        server.curr_time = _naive(sim_db.curr_time) or server.start_time
        server.sec_per_step = sim_db.sec_per_step or 10
        server.maze = Maze(sim_db.maze_name or "")
        server.step = sim_db.step

        # Load all active personas from DB.
        server.personas = {}
        server.personas_tile = {}

        persona_rows = PersonaModel.objects.filter(simulation=sim_db, status="active")
        for persona_row in persona_rows:
            curr_persona = Persona(persona_id=persona_row.pk)
            persona_name = curr_persona.name
            server.personas[persona_name] = curr_persona
            # personas_tile is reconstructed from the persisted curr_tile value.
            tile = curr_persona.scratch.curr_tile
            server.personas_tile[persona_name] = tuple(tile) if tile else (0, 0)  # type: ignore[arg-type]

        # Restore persona events on maze tiles.
        for persona_name, persona in server.personas.items():
            tile = server.personas_tile[persona_name]
            server.maze.tiles[tile[1]][tile[0]]["events"].add(persona.scratch.get_curr_event_and_desc())

        # Clean up previous step's object events (turn them idle) using the
        # game_obj_cleanup list saved from the last run_execute call.
        for entry in (sim_db.game_obj_cleanup or []):
            # Stored as [event_tuple, tile_xy] — tuples were serialized as lists.
            event_tuple, tile_xy = entry
            server.maze.turn_event_from_tile_idle(tuple(event_tuple), tuple(tile_xy))

        return server

    @classmethod
    def _get_step_cache(cls, sim_code: str, step: int, stage: str) -> Optional[dict]:
        """Load cached stage results from SimulationStepCache, or None if missing."""
        from translator.models import Simulation as SimulationModel  # noqa: PLC0415
        from translator.models import SimulationStepCache  # noqa: PLC0415

        try:
            sim_db = SimulationModel.objects.get(name=sim_code)
            cache = SimulationStepCache.objects.get(simulation=sim_db, step=step, stage=stage)
            return cache.data  # type: ignore[return-value]
        except Exception:
            return None

    @classmethod
    def _save_step_cache(cls, sim_code: str, step: int, stage: str, data: dict) -> None:
        """Persist stage results to SimulationStepCache (upsert)."""
        from translator.models import Simulation as SimulationModel  # noqa: PLC0415
        from translator.models import SimulationStepCache  # noqa: PLC0415

        sim_db = SimulationModel.objects.get(name=sim_code)
        SimulationStepCache.objects.update_or_create(
            simulation=sim_db,
            step=step,
            stage=stage,
            defaults={"data": data},
        )

    @classmethod
    def run_perceive(cls, sim_code: str) -> dict:
        """Stage 1: Perceive environment for all personas.

        Loads simulation state, runs perceive() for each persona (may include
        LLM poignancy scoring calls), saves perceived node_ids to StepCache.

        Returns: {"status": "ok", "step": N}
        """
        server = cls._load_for_stage(sim_code)
        cache_data: dict = {}

        for persona_name, persona in server.personas.items():
            perceived_nodes = persona.perceive(server.maze)
            # Serialize ConceptNodes as node_ids — they are reconstructed from DB
            # in subsequent stages by looking up a_mem.id_to_node.
            cache_data[persona_name] = {
                "perceived_node_ids": [node.node_id for node in perceived_nodes],
            }
            # Persist new concept nodes created during perceive (poignancy scores).
            persona.save()

        cls._save_step_cache(sim_code, server.step, "perceive", cache_data)
        return {"status": "ok", "step": server.step}

    @classmethod
    def run_retrieve(cls, sim_code: str) -> dict:
        """Stage 2: Retrieve relevant memories for perceived events.

        Runs Qdrant vector search for each persona's perceived events.
        No LLM calls — fast (1–3s total).

        Returns: {"status": "ok", "step": N}
        """
        server = cls._load_for_stage(sim_code)

        perceive_cache = cls._get_step_cache(sim_code, server.step, "perceive")
        if perceive_cache is None:
            raise RuntimeError(f"perceive cache missing for sim '{sim_code}' step {server.step}")

        cache_data: dict = {}

        for persona_name, persona in server.personas.items():
            persona_perceive = perceive_cache.get(persona_name, {})
            perceived_node_ids: list = persona_perceive.get("perceived_node_ids", [])

            # Reconstruct ConceptNode objects from persisted node_ids.
            perceived_nodes = [
                persona.a_mem.id_to_node[nid]
                for nid in perceived_node_ids
                if nid in persona.a_mem.id_to_node
            ]

            retrieved = persona.retrieve(perceived_nodes)

            # Serialize retrieved dict as node_ids.
            serialized: dict = {}
            for description, val in retrieved.items():
                curr_event = val.get("curr_event")
                serialized[description] = {
                    "curr_event_id": curr_event.node_id if curr_event else None,
                    "event_ids": [n.node_id for n in val.get("events", [])],
                    "thought_ids": [n.node_id for n in val.get("thoughts", [])],
                }
            cache_data[persona_name] = serialized

        cls._save_step_cache(sim_code, server.step, "retrieve", cache_data)
        return {"status": "ok", "step": server.step}

    @classmethod
    def run_plan(cls, sim_code: str) -> dict:
        """Stage 3: Generate plans for all personas (LLM-intensive).

        This is the slowest stage — typically 10–30s for 3 agents (2–5 LLM
        calls each). Saves act_address (plan string) to StepCache.

        Returns: {"status": "ok", "step": N}
        """
        server = cls._load_for_stage(sim_code)

        perceive_cache = cls._get_step_cache(sim_code, server.step, "perceive")
        retrieve_cache = cls._get_step_cache(sim_code, server.step, "retrieve")
        if perceive_cache is None or retrieve_cache is None:
            raise RuntimeError(f"perceive/retrieve cache missing for sim '{sim_code}' step {server.step}")

        cache_data: dict = {}

        for persona_name, persona in server.personas.items():
            # Determine new_day flag (same logic as persona.move()).
            new_day: Any = False
            if not persona.scratch.curr_time:
                new_day = "First day"
            elif persona.scratch.curr_time.strftime("%A %B %d") != server.curr_time.strftime("%A %B %d"):
                new_day = "New day"
            persona.scratch.curr_time = server.curr_time

            # Reconstruct retrieved dict from serialized node_ids.
            raw_retrieve = retrieve_cache.get(persona_name, {})
            retrieved: dict = {}
            for description, val in raw_retrieve.items():
                curr_event_id = val.get("curr_event_id")
                retrieved[description] = {
                    "curr_event": persona.a_mem.id_to_node.get(curr_event_id) if curr_event_id else None,
                    "events": [
                        persona.a_mem.id_to_node[nid]
                        for nid in val.get("event_ids", [])
                        if nid in persona.a_mem.id_to_node
                    ],
                    "thoughts": [
                        persona.a_mem.id_to_node[nid]
                        for nid in val.get("thought_ids", [])
                        if nid in persona.a_mem.id_to_node
                    ],
                }

            act_address = persona.plan(server.maze, server.personas, new_day, retrieved)
            cache_data[persona_name] = {
                "act_address": act_address,
                "new_day": new_day,
            }
            # Persist scratch changes (schedule, action fields) from plan.
            persona.save()

        cls._save_step_cache(sim_code, server.step, "plan", cache_data)
        return {"status": "ok", "step": server.step}

    @classmethod
    def run_reflect(cls, sim_code: str) -> dict:
        """Stage 4: Reflection — create new thoughts if importance threshold met.

        Conditionally calls LLMs (0–3 calls per persona). Fast if no reflection
        is triggered; up to 20s if all agents reflect.

        Returns: {"status": "ok", "step": N}
        """
        server = cls._load_for_stage(sim_code)

        for persona_name, persona in server.personas.items():
            persona.reflect()
            persona.save()

        cls._save_step_cache(sim_code, server.step, "reflect", {"completed": True})
        return {"status": "ok", "step": server.step}

    @classmethod
    def run_execute(cls, sim_code: str) -> dict:
        """Stage 5: Execute plans — pathfinding and movement finalization.

        No LLM calls. Computes next tile for each persona, writes MovementRecord
        to DB, updates Simulation.step and Simulation.game_obj_cleanup.

        Returns: {"movements": {persona_name: {movement, pronunciatio, description, chat}},
                  "meta": {"curr_time": "..."}, "step": N}
        """
        server = cls._load_for_stage(sim_code)

        plan_cache = cls._get_step_cache(sim_code, server.step, "plan")
        if plan_cache is None:
            raise RuntimeError(f"plan cache missing for sim '{sim_code}' step {server.step}")

        # Apply env positions — use latest EnvironmentState for the current step.
        from translator.models import EnvironmentState as EnvironmentStateModel  # noqa: PLC0415

        env_row = EnvironmentStateModel.objects.filter(
            simulation=server._db_sim, step=server.step
        ).first()
        if env_row:
            new_env = env_row.agent_positions or {}
            for persona_name, persona in server.personas.items():
                curr_tile = server.personas_tile[persona_name]
                new_tile_data = new_env.get(persona_name, {})
                new_tile = (int(new_tile_data.get("x", curr_tile[0])), int(new_tile_data.get("y", curr_tile[1])))
                server.personas_tile[persona_name] = new_tile
                server.maze.remove_subject_events_from_tile(persona.name, curr_tile)
                server.maze.add_event_from_tile(persona.scratch.get_curr_event_and_desc(), new_tile)

        # Track new object events for cleanup at next step start.
        new_game_obj_cleanup: list = []

        movements: dict = {"persona": {}, "meta": {}}
        for persona_name, persona in server.personas.items():
            persona_plan = plan_cache.get(persona_name, {})
            act_address = persona_plan.get("act_address")

            new_tile = server.personas_tile[persona_name]
            if not persona.scratch.planned_path:
                event_desc = persona.scratch.get_curr_obj_event_and_desc()
                new_game_obj_cleanup.append([list(event_desc), list(new_tile)])
                server.maze.add_event_from_tile(event_desc, new_tile)
                blank = (event_desc[0], None, None, None)
                server.maze.remove_event_from_tile(blank, new_tile)

            next_tile, pronunciatio, description = persona.execute(server.maze, server.personas, act_address)
            movements["persona"][persona_name] = {
                "movement": next_tile,
                "pronunciatio": pronunciatio,
                "description": description,
                "chat": persona.scratch.chat,
            }
            persona.save()

        movements["meta"]["curr_time"] = server.curr_time.strftime("%B %d, %Y, %H:%M:%S")

        next_step = server.step + 1
        next_time = server.curr_time + datetime.timedelta(seconds=server.sec_per_step)

        from django.db import transaction  # noqa: PLC0415
        from django.utils import timezone  # noqa: PLC0415
        from translator.models import MovementRecord as MovementRecordModel  # noqa: PLC0415
        from translator.models import Simulation as SimulationModel  # noqa: PLC0415

        curr_time_aware = timezone.make_aware(server.curr_time) if server.curr_time.tzinfo is None else server.curr_time
        next_time_aware = timezone.make_aware(next_time) if next_time.tzinfo is None else next_time

        with transaction.atomic():
            MovementRecordModel.objects.update_or_create(
                simulation=server._db_sim,
                step=server.step,
                defaults={
                    "sim_curr_time": curr_time_aware,
                    "persona_movements": movements,
                },
            )
            SimulationModel.objects.filter(pk=server._db_sim.pk).update(
                step=next_step,
                curr_time=next_time_aware,
                status="running",
                game_obj_cleanup=new_game_obj_cleanup,
            )
            set_runtime_state("curr_sim_code", {"sim_code": sim_code})
            set_runtime_state("curr_step", {"step": next_step})

        return {
            "movements": movements,
            "step": server.step,
            "next_step": next_step,
        }


if __name__ == "__main__":
    origin = input("Enter the name of the forked simulation: ").strip()
    target = input("Enter the name of the new simulation: ").strip()

    rs = ReverieServer(origin, target)
    rs.open_server()
