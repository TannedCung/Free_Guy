"""
Unit tests for plan.py (and its sub-modules) and reflect.py cognitive modules.

Tests verify:
- plan.py: daily plan generation, hourly decomposition, edge cases
- reflect.py: reflection trigger thresholds, importance scoring, focal point generation
"""

from __future__ import annotations

import datetime
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
def planning_persona(sample_persona: Any) -> Any:
    """Return a persona with extra fields needed for planning."""
    sample_persona.scratch.daily_req = [
        "wake up at 8am",
        "work on project 9am-12pm",
        "lunch at noon",
        "continue work 1-5pm",
        "relax in evening",
        "sleep at 11pm",
    ]
    sample_persona.scratch.f_daily_schedule = [
        ["sleeping", 480],
        ["working on project", 180],
        ["having lunch", 60],
        ["working on project", 240],
        ["relaxing", 360],
        ["sleeping", 120],
    ]
    sample_persona.scratch.f_daily_schedule_hourly_org = sample_persona.scratch.f_daily_schedule[:]
    return sample_persona


# ===========================================================================
# plan.py / daily_planning.py tests
# ===========================================================================


class TestGenerateWakeUpHour:
    def test_returns_integer(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """generate_wake_up_hour returns an integer (fail_safe=8 when LLM is mocked)."""
        from persona.cognitive_modules.daily_planning import generate_wake_up_hour

        result = generate_wake_up_hour(planning_persona)

        assert isinstance(result, int)

    def test_returns_reasonable_hour(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """generate_wake_up_hour returns a value between 0 and 23."""
        from persona.cognitive_modules.daily_planning import generate_wake_up_hour

        result = generate_wake_up_hour(planning_persona)

        assert 0 <= result <= 23


class TestGenerateFirstDailyPlan:
    def test_returns_nonempty_list(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """generate_first_daily_plan returns a non-empty list of strings."""
        from persona.cognitive_modules.daily_planning import generate_first_daily_plan

        result = generate_first_daily_plan(planning_persona, wake_up_hour=8)

        assert isinstance(result, list)
        assert len(result) >= 1

    def test_first_entry_contains_wake_up(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """The first entry in the daily plan mentions waking up at the specified hour."""
        from persona.cognitive_modules.daily_planning import generate_first_daily_plan

        result = generate_first_daily_plan(planning_persona, wake_up_hour=7)

        # The function prepends a wake-up entry with the given hour.
        assert any("7:00 am" in entry for entry in result)

    def test_all_entries_are_strings(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """Every entry in the returned list is a string."""
        from persona.cognitive_modules.daily_planning import generate_first_daily_plan

        result = generate_first_daily_plan(planning_persona, wake_up_hour=8)

        for entry in result:
            assert isinstance(entry, str)


class TestGenerateHourlySchedule:
    def test_returns_list_of_pairs(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """generate_hourly_schedule returns a list where each item is [task, duration]."""
        from persona.cognitive_modules.daily_planning import generate_hourly_schedule

        # Use a high wake_up_hour to minimise LLM calls (fewer non-sleep hours).
        result = generate_hourly_schedule(planning_persona, wake_up_hour=20)

        assert isinstance(result, list)
        assert len(result) >= 1
        for pair in result:
            assert len(pair) == 2
            assert isinstance(pair[0], str)
            assert isinstance(pair[1], int)

    def test_total_duration_equals_24_hours(self, mock_provider_injected: Any, planning_persona: Any) -> None:
        """The sum of all activity durations equals exactly 1440 minutes (24 hours)."""
        from persona.cognitive_modules.daily_planning import generate_hourly_schedule

        result = generate_hourly_schedule(planning_persona, wake_up_hour=20)

        total_minutes = sum(duration for _, duration in result)
        assert total_minutes == 1440

    def test_zero_wake_up_hour_produces_no_sleeping_prefix(
        self, mock_provider_injected: Any, planning_persona: Any
    ) -> None:
        """With wake_up_hour=0, the hourly schedule still sums to 24 hours."""
        from persona.cognitive_modules.daily_planning import generate_hourly_schedule

        result = generate_hourly_schedule(planning_persona, wake_up_hour=0)

        total_minutes = sum(duration for _, duration in result)
        assert total_minutes == 1440


# ===========================================================================
# reflect.py tests
# ===========================================================================


class TestReflectionTrigger:
    def test_returns_false_when_importance_above_zero(self, sample_persona: Any) -> None:
        """reflection_trigger returns False when importance_trigger_curr > 0."""
        from persona.cognitive_modules.reflect import reflection_trigger

        sample_persona.scratch.importance_trigger_curr = 50

        assert reflection_trigger(sample_persona) is False

    def test_returns_true_when_importance_zero_and_memory_nonempty(self, sample_persona: Any) -> None:
        """reflection_trigger returns True when counter reaches 0 and memory has events."""
        from persona.cognitive_modules.reflect import reflection_trigger

        sample_persona.scratch.importance_trigger_curr = 0
        # sample_persona already has events in a_mem.seq_event from sample_memory fixture.
        assert len(sample_persona.a_mem.seq_event) > 0

        assert reflection_trigger(sample_persona) is True

    def test_returns_false_when_importance_zero_but_memory_empty(self, sample_persona: Any) -> None:
        """reflection_trigger returns False when counter is 0 but no events or thoughts."""
        from persona.cognitive_modules.reflect import reflection_trigger

        sample_persona.scratch.importance_trigger_curr = 0
        sample_persona.a_mem.seq_event = []
        sample_persona.a_mem.seq_thought = []

        assert reflection_trigger(sample_persona) is False

    def test_returns_false_when_importance_negative_and_memory_empty(self, sample_persona: Any) -> None:
        """reflection_trigger handles negative importance_trigger_curr without error."""
        from persona.cognitive_modules.reflect import reflection_trigger

        sample_persona.scratch.importance_trigger_curr = -10
        sample_persona.a_mem.seq_event = []
        sample_persona.a_mem.seq_thought = []

        assert reflection_trigger(sample_persona) is False


class TestResetReflectionCounter:
    def test_restores_importance_trigger_curr_to_max(self, sample_persona: Any) -> None:
        """reset_reflection_counter sets importance_trigger_curr back to importance_trigger_max."""
        from persona.cognitive_modules.reflect import reset_reflection_counter

        sample_persona.scratch.importance_trigger_max = 150
        sample_persona.scratch.importance_trigger_curr = 0

        reset_reflection_counter(sample_persona)

        assert sample_persona.scratch.importance_trigger_curr == 150

    def test_resets_importance_ele_n_to_zero(self, sample_persona: Any) -> None:
        """reset_reflection_counter zeroes out the importance element counter."""
        from persona.cognitive_modules.reflect import reset_reflection_counter

        sample_persona.scratch.importance_ele_n = 42

        reset_reflection_counter(sample_persona)

        assert sample_persona.scratch.importance_ele_n == 0


class TestGeneratePoigScore:
    def test_idle_description_returns_one_without_llm(self, sample_persona: Any) -> None:
        """generate_poig_score returns 1 for 'is idle' descriptions without any LLM call."""
        from persona.cognitive_modules.reflect import generate_poig_score

        # No LLM provider injected — should work because "is idle" short-circuits.
        result = generate_poig_score(sample_persona, "event", "Test Agent is idle")

        assert result == 1

    def test_event_type_returns_integer(self, mock_provider_injected: Any, sample_persona: Any) -> None:
        """generate_poig_score returns an integer for event-type descriptions."""
        from persona.cognitive_modules.reflect import generate_poig_score

        result = generate_poig_score(sample_persona, "event", "Test Agent is working hard")

        # With mock LLM, fail_safe = 4 (see run_gpt_prompt_event_poignancy)
        assert isinstance(result, int)

    def test_unknown_type_returns_none(self, sample_persona: Any) -> None:
        """generate_poig_score returns None for unrecognised event types."""
        from persona.cognitive_modules.reflect import generate_poig_score

        result = generate_poig_score(sample_persona, "unknown_type", "some description")

        assert result is None


class TestGenerateFocalPoints:
    def test_returns_list_of_strings(self, mock_provider_injected: Any, sample_persona: Any) -> None:
        """generate_focal_points returns a list of strings."""
        from persona.cognitive_modules.reflect import generate_focal_points

        result = generate_focal_points(sample_persona, n=3)

        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, str)

    def test_returns_n_focal_points(self, mock_provider_injected: Any, sample_persona: Any) -> None:
        """generate_focal_points returns exactly n focal points (or fail_safe of size n)."""
        from persona.cognitive_modules.reflect import generate_focal_points

        n = 3
        result = generate_focal_points(sample_persona, n=n)

        # fail_safe is ["Who am I"] * n so len should be n.
        assert len(result) == n

    def test_works_with_empty_memory(self, mock_provider_injected: Any, sample_persona: Any) -> None:
        """generate_focal_points handles a persona with no events or thoughts gracefully."""
        from persona.cognitive_modules.reflect import generate_focal_points

        # Clear all events and thoughts to test the empty-memory path.
        sample_persona.a_mem.seq_event = []
        sample_persona.a_mem.seq_thought = []

        # Should not raise — returns the fail_safe list.
        result = generate_focal_points(sample_persona, n=2)

        assert isinstance(result, list)
