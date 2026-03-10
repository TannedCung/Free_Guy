"""
Smoke tests that verify the test fixture setup is functional.

These tests do not exercise simulation logic — they confirm that fixtures are
correctly constructed and the test suite can be run without a live LLM or
real data files on disk.
"""

import datetime
from typing import Any

from llm.protocol import LLMProvider

# ---------------------------------------------------------------------------
# mock_llm_provider
# ---------------------------------------------------------------------------


def test_mock_llm_provider_satisfies_protocol(mock_llm_provider: Any) -> None:
    """MockLLMProvider must satisfy the LLMProvider Protocol at runtime."""
    assert isinstance(mock_llm_provider, LLMProvider)


def test_mock_llm_provider_complete(mock_llm_provider: Any) -> None:
    result = mock_llm_provider.complete("Say hello.")
    assert isinstance(result, str)
    assert result == "okay"
    assert mock_llm_provider.call_log[-1]["method"] == "complete"


def test_mock_llm_provider_chat(mock_llm_provider: Any) -> None:
    messages = [{"role": "user", "content": "Hi"}]
    result = mock_llm_provider.chat(messages)
    assert isinstance(result, str)
    assert mock_llm_provider.call_log[-1]["method"] == "chat"


def test_mock_llm_provider_embed(mock_llm_provider: Any) -> None:
    vec = mock_llm_provider.embed("some text")
    assert isinstance(vec, list)
    assert all(isinstance(v, float) for v in vec)
    assert len(vec) == 8


def test_mock_llm_provider_records_all_calls(mock_llm_provider: Any) -> None:
    mock_llm_provider.complete("a")
    mock_llm_provider.chat([{"role": "user", "content": "b"}])
    mock_llm_provider.embed("c")
    assert len(mock_llm_provider.call_log) == 3


# ---------------------------------------------------------------------------
# sample_memory
# ---------------------------------------------------------------------------


def test_sample_memory_has_events(sample_memory: Any) -> None:
    assert len(sample_memory.seq_event) == 2


def test_sample_memory_has_thoughts(sample_memory: Any) -> None:
    assert len(sample_memory.seq_thought) == 1


def test_sample_memory_embeddings_populated(sample_memory: Any) -> None:
    assert len(sample_memory.embeddings) > 0
    for key, vec in sample_memory.embeddings.items():
        assert isinstance(vec, list)
        assert len(vec) == 8


def test_sample_memory_keyword_index(sample_memory: Any) -> None:
    assert "working" in sample_memory.kw_to_event or "test agent" in sample_memory.kw_to_event


# ---------------------------------------------------------------------------
# sample_scratch
# ---------------------------------------------------------------------------


def test_sample_scratch_identity(sample_scratch: Any) -> None:
    assert sample_scratch.name == "Test Agent"
    assert sample_scratch.age == 30
    assert isinstance(sample_scratch.innate, str)


def test_sample_scratch_curr_time(sample_scratch: Any) -> None:
    assert isinstance(sample_scratch.curr_time, datetime.datetime)


def test_sample_scratch_defaults_are_set(sample_scratch: Any) -> None:
    assert sample_scratch.vision_r == 4
    assert sample_scratch.att_bandwidth == 3


# ---------------------------------------------------------------------------
# sample_persona
# ---------------------------------------------------------------------------


def test_sample_persona_has_name(sample_persona: Any) -> None:
    assert sample_persona.name == "Test Agent"


def test_sample_persona_has_memory_components(sample_persona: Any) -> None:
    assert sample_persona.scratch is not None
    assert sample_persona.a_mem is not None
    assert sample_persona.s_mem is not None


def test_sample_persona_spatial_memory_tree(sample_persona: Any) -> None:
    assert "the_ville" in sample_persona.s_mem.tree


# ---------------------------------------------------------------------------
# sample_maze
# ---------------------------------------------------------------------------


def test_sample_maze_dimensions(sample_maze: Any) -> None:
    assert sample_maze.maze_width == 5
    assert sample_maze.maze_height == 5
    assert len(sample_maze.tiles) == 5
    assert len(sample_maze.tiles[0]) == 5


def test_sample_maze_border_is_collision(sample_maze: Any) -> None:
    # Top-left corner should be a collision tile.
    assert sample_maze.tiles[0][0]["collision"] is True


def test_sample_maze_interior_is_passable(sample_maze: Any) -> None:
    # Centre tile should be passable.
    assert sample_maze.tiles[2][2]["collision"] is False


def test_sample_maze_address_tiles(sample_maze: Any) -> None:
    assert "test_world:test_sector" in sample_maze.address_tiles
    coords = sample_maze.address_tiles["test_world:test_sector"]
    assert len(coords) > 0


def test_sample_maze_spawn_location(sample_maze: Any) -> None:
    assert "<spawn_loc>spawn-a" in sample_maze.address_tiles
    assert (2, 2) in sample_maze.address_tiles["<spawn_loc>spawn-a"]
