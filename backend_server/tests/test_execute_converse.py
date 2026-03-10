"""
Unit tests for execute.py and converse.py cognitive modules.

Tests verify:
- execute.py: action execution produces valid output, emoji assignment works, handles edge cases
- converse.py: conversation initiation logic, dialogue generation, poignancy scoring
"""

from __future__ import annotations

from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider_injected(mock_llm_provider: Any) -> Any:
    """Inject the mock LLM provider into llm_bridge and clean up after."""
    from persona.prompt_template import llm_bridge

    llm_bridge.set_provider(mock_llm_provider)
    yield mock_llm_provider
    llm_bridge._provider = None  # type: ignore[attr-defined]


@pytest.fixture
def execute_persona(sample_persona: Any) -> Any:
    """Return a persona configured for execute tests."""
    sample_persona.scratch.curr_tile = (2, 2)
    sample_persona.scratch.act_path_set = False
    sample_persona.scratch.planned_path = []
    sample_persona.scratch.act_description = "working on a project"
    sample_persona.scratch.act_address = "test_world:test_sector:test_arena"
    sample_persona.scratch.act_pronunciatio = "\U0001f4bb"  # 💻
    return sample_persona


@pytest.fixture
def target_persona(sample_persona: Any) -> Any:
    """Return a second persona for conversation tests."""
    import datetime

    from persona.memory_structures.associative_memory import AssociativeMemory
    from persona.memory_structures.scratch import Scratch
    from persona.memory_structures.spatial_memory import MemoryTree
    from persona.persona import Persona

    p2: Persona = object.__new__(Persona)
    p2.name = "Other Agent"

    scratch2 = Scratch("/nonexistent/path/scratch2.json")
    scratch2.name = "Other Agent"
    scratch2.first_name = "Other"
    scratch2.last_name = "Agent"
    scratch2.age = 25
    scratch2.innate = "cheerful"
    scratch2.learned = "Other Agent works at the coffee shop."
    scratch2.currently = "making coffee"
    scratch2.lifestyle = "Other Agent keeps a busy schedule."
    scratch2.living_area = "the_ville:double studio"
    scratch2.curr_time = datetime.datetime(2023, 1, 1, 9, 0, 0)
    scratch2.curr_tile = (1, 1)
    scratch2.daily_plan_req = "Other Agent should serve customers today."
    scratch2.act_description = "making coffee"
    p2.scratch = scratch2

    mem2: AssociativeMemory = object.__new__(AssociativeMemory)
    mem2.id_to_node = {}
    mem2.seq_event = []
    mem2.seq_thought = []
    mem2.seq_chat = []
    mem2.kw_to_event = {}
    mem2.kw_to_thought = {}
    mem2.kw_to_chat = {}
    mem2.kw_strength_event = {}
    mem2.kw_strength_thought = {}
    mem2.embeddings = {}
    p2.a_mem = mem2

    p2.s_mem = MemoryTree("/nonexistent/path/spatial_memory2.json")
    p2.s_mem.tree = {}

    return p2


# ===========================================================================
# execute.py tests
# ===========================================================================


class TestExecuteWaitingPlan:
    def test_waiting_plan_returns_tuple(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() with <waiting> plan returns a 3-tuple."""
        from persona.cognitive_modules.execute import execute

        plan = "<waiting> 2 2"
        result = execute(execute_persona, sample_maze, {}, plan)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_waiting_plan_sets_act_path(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() with <waiting> plan sets act_path_set=True."""
        from persona.cognitive_modules.execute import execute

        plan = "<waiting> 2 2"
        execute(execute_persona, sample_maze, {}, plan)

        assert execute_persona.scratch.act_path_set is True

    def test_waiting_plan_description_contains_action(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() description field contains the act_description."""
        from persona.cognitive_modules.execute import execute

        plan = "<waiting> 2 2"
        tile, pronunciatio, description = execute(execute_persona, sample_maze, {}, plan)

        assert execute_persona.scratch.act_description in description
        assert execute_persona.scratch.act_address in description


class TestExecuteAddressPlan:
    def test_address_plan_returns_valid_tile(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() with address plan returns a tile that is a 2-element coordinate."""
        from persona.cognitive_modules.execute import execute

        plan = "test_world:test_sector:test_arena"
        tile, pronunciatio, description = execute(execute_persona, sample_maze, {}, plan)

        # tile should be a tuple/list of length 2
        assert len(tile) == 2

    def test_address_plan_emoji_in_output(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() returns the persona's act_pronunciatio as the second element."""
        from persona.cognitive_modules.execute import execute

        plan = "test_world:test_sector:test_arena"
        tile, pronunciatio, description = execute(execute_persona, sample_maze, {}, plan)

        assert pronunciatio == execute_persona.scratch.act_pronunciatio


class TestExecuteExistingPath:
    def test_existing_path_skips_recalculation(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() with act_path_set=True follows existing planned_path without rebuilding."""
        from persona.cognitive_modules.execute import execute

        execute_persona.scratch.act_path_set = True
        execute_persona.scratch.planned_path = [(3, 2), (3, 3)]

        tile, pronunciatio, description = execute(execute_persona, sample_maze, {}, "irrelevant_plan")

        # Should advance to the first step in planned_path
        assert tile == (3, 2)
        # Remaining path should have one element
        assert execute_persona.scratch.planned_path == [(3, 3)]

    def test_empty_path_stays_at_curr_tile(self, execute_persona: Any, sample_maze: Any) -> None:
        """execute() with act_path_set=True and empty path stays at curr_tile."""
        from persona.cognitive_modules.execute import execute

        execute_persona.scratch.act_path_set = True
        execute_persona.scratch.planned_path = []

        tile, pronunciatio, description = execute(execute_persona, sample_maze, {}, "irrelevant_plan")

        assert tile == execute_persona.scratch.curr_tile


# ===========================================================================
# converse.py tests
# ===========================================================================


class TestGeneratePoigScore:
    def test_idle_description_returns_1_without_llm(self, sample_persona: Any) -> None:
        """generate_poig_score returns 1 for 'is idle' description, bypassing LLM."""
        from persona.cognitive_modules.converse import generate_poig_score

        result = generate_poig_score(sample_persona, "event", "Test Agent is idle")

        assert result == 1

    def test_event_type_returns_integer(
        self, mock_provider_injected: Any, execute_persona: Any
    ) -> None:
        """generate_poig_score for 'event' type returns an integer (fail_safe=4)."""
        from persona.cognitive_modules.converse import generate_poig_score

        result = generate_poig_score(execute_persona, "event", "working on a project")

        assert isinstance(result, int)

    def test_chat_type_returns_integer(
        self, mock_provider_injected: Any, execute_persona: Any
    ) -> None:
        """generate_poig_score for 'chat' type returns an integer (fail_safe=4)."""
        from persona.cognitive_modules.converse import generate_poig_score

        result = generate_poig_score(execute_persona, "chat", "talking with someone")

        assert isinstance(result, int)

    def test_unknown_type_returns_none(self, sample_persona: Any) -> None:
        """generate_poig_score for an unknown event_type returns None."""
        from persona.cognitive_modules.converse import generate_poig_score

        result = generate_poig_score(sample_persona, "unknown_type", "some description")

        assert result is None


class TestGenerateActionEventTriple:
    def test_returns_three_element_tuple(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_action_event_triple returns a 3-tuple."""
        from persona.cognitive_modules.converse import generate_action_event_triple

        result = generate_action_event_triple("cooking breakfast", sample_persona)

        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_returns_strings(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_action_event_triple elements are all strings."""
        from persona.cognitive_modules.converse import generate_action_event_triple

        s, p, o = generate_action_event_triple("reading a book", sample_persona)

        assert isinstance(s, str)
        assert isinstance(p, str)
        assert isinstance(o, str)

    def test_subject_is_persona_name(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_action_event_triple subject is always the persona's name."""
        from persona.cognitive_modules.converse import generate_action_event_triple

        s, p, o = generate_action_event_triple("sleeping", sample_persona)

        assert s == sample_persona.scratch.name


class TestGenerateInnerThought:
    def test_returns_string(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_inner_thought returns a string."""
        from persona.cognitive_modules.converse import generate_inner_thought

        result = generate_inner_thought(sample_persona, "I should call my friend.")

        assert isinstance(result, str)

    def test_returns_nonempty_string(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_inner_thought returns a non-empty string."""
        from persona.cognitive_modules.converse import generate_inner_thought

        result = generate_inner_thought(sample_persona, "I need to finish this task.")

        assert len(result) > 0


class TestGenerateNextLine:
    def test_returns_string(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_next_line returns a string."""
        from persona.cognitive_modules.converse import generate_next_line

        curr_convo = [["Interviewer", "How are you today?"]]
        result = generate_next_line(sample_persona, "Interviewer", curr_convo, "feeling productive")

        assert isinstance(result, str)

    def test_handles_empty_convo(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_next_line handles an empty conversation history."""
        from persona.cognitive_modules.converse import generate_next_line

        result = generate_next_line(sample_persona, "Interviewer", [], "no prior context")

        assert isinstance(result, str)

    def test_handles_multi_turn_convo(
        self, mock_provider_injected: Any, sample_persona: Any
    ) -> None:
        """generate_next_line works with a multi-turn conversation."""
        from persona.cognitive_modules.converse import generate_next_line

        curr_convo = [
            ["Interviewer", "What are you working on?"],
            [sample_persona.scratch.name, "A software project."],
            ["Interviewer", "Interesting! Tell me more."],
        ]
        result = generate_next_line(
            sample_persona, "Interviewer", curr_convo, "working on software"
        )

        assert isinstance(result, str)
