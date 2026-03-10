"""
Unit tests for perceive.py and retrieve.py cognitive modules.

Tests verify perception logic (vision radius, attention bandwidth, retention)
and memory retrieval logic (recency scoring, importance scoring, relevance
scoring, combined scoring).
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from persona.memory_structures.associative_memory import ConceptNode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_event_to_tile(maze: Any, col: int, row: int, s: str, p: str, o: str, desc: str) -> None:
    """Add a 4-tuple event to a specific maze tile."""
    maze.tiles[row][col]["events"].add((s, p, o, desc))


# ---------------------------------------------------------------------------
# Fixtures for perceive/retrieve tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_provider_injected(mock_llm_provider: Any) -> Any:
    """Inject the mock LLM provider into llm_bridge and clean up after."""
    from persona.prompt_template import llm_bridge

    llm_bridge.set_provider(mock_llm_provider)
    yield mock_llm_provider
    # Reset so other tests get a fresh provider.
    llm_bridge._provider = None  # type: ignore[attr-defined]


@pytest.fixture
def persona_at_center(sample_persona: Any) -> Any:
    """Return a persona positioned at tile (2, 2) — the center of the 5x5 test maze."""
    sample_persona.scratch.curr_tile = (2, 2)
    sample_persona.scratch.vision_r = 4
    sample_persona.scratch.att_bandwidth = 3
    sample_persona.scratch.retention = 5
    sample_persona.scratch.importance_trigger_curr = 150
    sample_persona.scratch.importance_ele_n = 0
    return sample_persona


# ===========================================================================
# perceive.py tests
# ===========================================================================


class TestPerceive:
    def test_perceive_nearby_events_added_to_memory(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """Agent perceives a new event on a nearby tile and stores it in memory."""
        from persona.cognitive_modules.perceive import perceive

        # Place one event on an adjacent interior tile (1,1) — same arena as (2,2).
        _add_event_to_tile(sample_maze, 1, 1, "coffee maker", "is", "brewing", "coffee maker is brewing")

        initial_event_count = len(persona_at_center.a_mem.seq_event)

        ret = perceive(persona_at_center, sample_maze)

        # One new ConceptNode should be returned.
        assert len(ret) >= 1
        # Memory should have grown.
        assert len(persona_at_center.a_mem.seq_event) > initial_event_count

    def test_perceive_returns_concept_nodes(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """perceive() returns ConceptNode instances, not raw event tuples."""
        from persona.cognitive_modules.perceive import perceive

        _add_event_to_tile(sample_maze, 2, 1, "desk", "is", "occupied", "desk is occupied")

        ret = perceive(persona_at_center, sample_maze)

        for node in ret:
            assert isinstance(node, ConceptNode)

    def test_perceive_respects_att_bandwidth(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """Only att_bandwidth (3) closest events are perceived even if more are available."""
        from persona.cognitive_modules.perceive import perceive

        persona_at_center.scratch.att_bandwidth = 2

        # Add 4 events to different interior tiles within vision radius.
        _add_event_to_tile(sample_maze, 1, 1, "obj_a", "is", "active", "obj_a is active")
        _add_event_to_tile(sample_maze, 1, 2, "obj_b", "is", "active", "obj_b is active")
        _add_event_to_tile(sample_maze, 2, 1, "obj_c", "is", "active", "obj_c is active")
        _add_event_to_tile(sample_maze, 3, 3, "obj_d", "is", "active", "obj_d is active")

        ret = perceive(persona_at_center, sample_maze)

        # At most att_bandwidth=2 events should be returned.
        assert len(ret) <= persona_at_center.scratch.att_bandwidth

    def test_perceive_skips_events_already_in_memory(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """Events that match latest_events (within retention) are not re-added."""
        from persona.cognitive_modules.perceive import perceive

        # First perception — event enters memory.
        _add_event_to_tile(sample_maze, 1, 1, "chair", "is", "empty", "chair is empty")
        first_pass = perceive(persona_at_center, sample_maze)
        assert len(first_pass) >= 1

        # Event is now in latest_events — second perception should skip it.
        second_pass = perceive(persona_at_center, sample_maze)
        assert len(second_pass) == 0

    def test_perceive_ignores_events_outside_vision_radius(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """Events on tiles outside vision_r are not perceived."""
        from persona.cognitive_modules.perceive import perceive

        # Use a 3x3 maze placed far from the persona so no tile is reachable.
        # Simplest approach: reduce vision_r to 0 (persona sees only its own tile).
        persona_at_center.scratch.vision_r = 0

        # Place event on an adjacent tile (not on the persona's tile).
        _add_event_to_tile(sample_maze, 1, 1, "far_obj", "is", "humming", "far_obj is humming")

        ret = perceive(persona_at_center, sample_maze)

        # Nothing on the persona's own tile (2,2) has an event.
        assert len(ret) == 0

    def test_perceive_idle_event_gets_poignancy_one(
        self, mock_provider_injected: Any, persona_at_center: Any, sample_maze: Any
    ) -> None:
        """Events with 'is idle' description receive poignancy 1 without an LLM call."""
        from persona.cognitive_modules.perceive import perceive

        _add_event_to_tile(sample_maze, 2, 1, "lamp", "is", "idle", "lamp is idle")

        ret = perceive(persona_at_center, sample_maze)

        # The event should be perceived and stored.
        assert len(ret) >= 1
        # poignancy for idle events is hardcoded to 1.
        idle_node = ret[0]
        assert idle_node.poignancy == 1


# ===========================================================================
# retrieve.py tests
# ===========================================================================


class TestRetrieveBasic:
    def test_retrieve_structure(self, sample_persona: Any, sample_memory: Any) -> None:
        """retrieve() returns a dict keyed by event description with the expected sub-keys."""
        from persona.cognitive_modules.retrieve import retrieve

        # Use the first event already in sample_memory as a perceived event.
        perceived_event = sample_memory.seq_event[0]

        result = retrieve(sample_persona, [perceived_event])

        assert perceived_event.description in result
        entry = result[perceived_event.description]
        assert "curr_event" in entry
        assert "events" in entry
        assert "thoughts" in entry

    def test_retrieve_curr_event_matches_input(self, sample_persona: Any, sample_memory: Any) -> None:
        """The 'curr_event' in each retrieved entry matches the input perceived event."""
        from persona.cognitive_modules.retrieve import retrieve

        perceived = sample_memory.seq_event[0]
        result = retrieve(sample_persona, [perceived])

        assert result[perceived.description]["curr_event"] is perceived

    def test_retrieve_multiple_events(self, sample_persona: Any, sample_memory: Any) -> None:
        """retrieve() handles multiple perceived events, returning one entry per event."""
        from persona.cognitive_modules.retrieve import retrieve

        perceived = sample_memory.seq_event  # list of 2 events
        result = retrieve(sample_persona, perceived)

        assert len(result) == len(perceived)


class TestExtractScoring:
    def test_extract_recency_most_recent_scores_highest(self, sample_persona: Any, sample_memory: Any) -> None:
        """extract_recency assigns higher score to the first node (most recent order)."""
        from persona.cognitive_modules.retrieve import extract_recency

        nodes = list(sample_memory.seq_event)  # 2 nodes in chronological order
        recency = extract_recency(sample_persona, nodes)

        # First node in list gets recency_decay^1, second gets recency_decay^2.
        # decay < 1, so first node has higher score.
        node_ids = [n.node_id for n in nodes]
        assert recency[node_ids[0]] > recency[node_ids[1]]

    def test_extract_importance_reflects_poignancy(self, sample_persona: Any, sample_memory: Any) -> None:
        """extract_importance returns each node's poignancy as its importance score."""
        from persona.cognitive_modules.retrieve import extract_importance

        nodes = list(sample_memory.seq_event)
        importance = extract_importance(sample_persona, nodes)

        for node in nodes:
            assert importance[node.node_id] == node.poignancy

    def test_extract_importance_higher_poignancy_scores_higher(
        self, sample_persona: Any, sample_memory: Any
    ) -> None:
        """Node with higher poignancy scores higher in importance extraction."""
        from persona.cognitive_modules.retrieve import extract_importance

        nodes = list(sample_memory.seq_event)
        # seq_event is prepended — index 0 is most-recently-added ("eating lunch", poignancy=2.0),
        # index 1 is first-added ("working", poignancy=3.0).
        importance = extract_importance(sample_persona, nodes)

        higher_node = max(nodes, key=lambda n: n.poignancy)
        lower_node = min(nodes, key=lambda n: n.poignancy)
        assert importance[higher_node.node_id] > importance[lower_node.node_id]

    def test_normalize_dict_floats_range(self) -> None:
        """normalize_dict_floats maps values to [target_min, target_max]."""
        from persona.cognitive_modules.retrieve import normalize_dict_floats

        d = {"a": 1.0, "b": 3.0, "c": 5.0}
        result = normalize_dict_floats(d, 0.0, 1.0)

        assert min(result.values()) >= 0.0
        assert max(result.values()) <= 1.0

    def test_normalize_dict_floats_equal_values(self) -> None:
        """normalize_dict_floats handles all-equal values (zero range) without error."""
        from persona.cognitive_modules.retrieve import normalize_dict_floats

        d = {"a": 5.0, "b": 5.0, "c": 5.0}
        result = normalize_dict_floats(d, 0.0, 1.0)

        # All values should be set to mid-range = 0.5.
        for v in result.values():
            assert v == pytest.approx(0.5)

    def test_top_highest_x_values(self) -> None:
        """top_highest_x_values returns the x highest scoring entries."""
        from persona.cognitive_modules.retrieve import top_highest_x_values

        d = {"a": 1.0, "b": 4.0, "c": 2.0, "d": 3.0}
        result = top_highest_x_values(d, 2)

        assert set(result.keys()) == {"b", "d"}


class TestNewRetrieve:
    def test_new_retrieve_returns_nodes_for_focal_point(
        self, mock_provider_injected: Any, sample_persona: Any, sample_memory: Any
    ) -> None:
        """new_retrieve() returns a list of ConceptNodes for each focal point."""
        from persona.cognitive_modules.retrieve import new_retrieve

        result = new_retrieve(sample_persona, ["working on a task"])

        assert "working on a task" in result
        assert isinstance(result["working on a task"], list)
        for node in result["working on a task"]:
            assert isinstance(node, ConceptNode)

    def test_new_retrieve_multiple_focal_points(
        self, mock_provider_injected: Any, sample_persona: Any, sample_memory: Any
    ) -> None:
        """new_retrieve() handles multiple focal points, one entry per point."""
        from persona.cognitive_modules.retrieve import new_retrieve

        focal_pts = ["working", "eating lunch"]
        result = new_retrieve(sample_persona, focal_pts)

        assert set(result.keys()) == set(focal_pts)

    def test_new_retrieve_excludes_idle_nodes(
        self, mock_provider_injected: Any, sample_persona: Any, sample_memory: Any
    ) -> None:
        """new_retrieve skips nodes whose embedding_key contains 'idle'."""
        import datetime as dt

        from persona.cognitive_modules.retrieve import new_retrieve

        # Add an idle event to memory.
        sample_memory.add_event(
            created=dt.datetime(2023, 1, 1, 11, 0, 0),
            expiration=None,
            s="Test Agent",
            p="is",
            o="idle",
            description="Test Agent is idle",
            keywords={"test agent", "idle"},
            poignancy=1.0,
            embedding_pair=("Test Agent is idle", [0.4] * 8),
            filling=[],
        )

        result = new_retrieve(sample_persona, ["idle behavior"])

        returned_keys = [n.embedding_key for n in result["idle behavior"]]
        assert "Test Agent is idle" not in returned_keys

    def test_new_retrieve_n_count_limits_results(
        self, mock_provider_injected: Any, sample_persona: Any, sample_memory: Any
    ) -> None:
        """new_retrieve respects the n_count parameter."""
        from persona.cognitive_modules.retrieve import new_retrieve

        result = new_retrieve(sample_persona, ["task"], n_count=1)

        # At most 1 node should be returned.
        assert len(result["task"]) <= 1
