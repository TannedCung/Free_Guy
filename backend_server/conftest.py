"""
Shared pytest fixtures for the backend_server test suite.

Note: OPENAI_API_KEY must be set before any module-level imports from
constant.py, which raises ValueError at import time if the key is missing.
This conftest.py sets a dummy value as the very first action.
"""

import datetime
import os
from typing import Any

# Set required env vars BEFORE any application imports that check them.
os.environ.setdefault("OPENAI_API_KEY", "test-key-for-testing")

import pytest  # noqa: E402

from persona.memory_structures.associative_memory import AssociativeMemory  # noqa: E402
from persona.memory_structures.scratch import Scratch  # noqa: E402
from persona.memory_structures.spatial_memory import MemoryTree  # noqa: E402

# ---------------------------------------------------------------------------
# MockLLMProvider
# ---------------------------------------------------------------------------


class MockLLMProvider:
    """Canned LLM provider that returns predictable responses for any prompt.

    Satisfies the LLMProvider Protocol without making any real API calls.
    """

    def __init__(self, chat_response: str = "okay", embed_dim: int = 8) -> None:
        self._chat_response = chat_response
        self._embed_dim = embed_dim
        self.call_log: list[dict[str, Any]] = []

    def complete(self, prompt: str, **kwargs: Any) -> str:
        self.call_log.append({"method": "complete", "prompt": prompt, "kwargs": kwargs})
        return self._chat_response

    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        self.call_log.append({"method": "chat", "messages": messages, "kwargs": kwargs})
        return self._chat_response

    def embed(self, text: str) -> list[float]:
        self.call_log.append({"method": "embed", "text": text})
        # Return a unit vector of the configured dimension.
        return [1.0 / self._embed_dim] * self._embed_dim


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm_provider() -> MockLLMProvider:
    """Return a MockLLMProvider that records calls and returns canned responses."""
    return MockLLMProvider()


@pytest.fixture
def sample_memory() -> AssociativeMemory:
    """Return an AssociativeMemory instance pre-populated with test events and thoughts.

    Bypasses file I/O by constructing the object via object.__new__() and
    initialising internal data structures directly.
    """
    mem: AssociativeMemory = object.__new__(AssociativeMemory)

    # Initialise all internal fields (mirrors AssociativeMemory.__init__ setup).
    mem.id_to_node = {}
    mem.seq_event = []
    mem.seq_thought = []
    mem.seq_chat = []
    mem.kw_to_event = {}
    mem.kw_to_thought = {}
    mem.kw_to_chat = {}
    mem.kw_strength_event = {}
    mem.kw_strength_thought = {}
    mem.embeddings = {}

    base_time = datetime.datetime(2023, 1, 1, 9, 0, 0)
    embed_dim = 8

    # Add two events.
    mem.add_event(
        created=base_time,
        expiration=None,
        s="Test Agent",
        p="is",
        o="working",
        description="Test Agent is working",
        keywords={"test agent", "working"},
        poignancy=3.0,
        embedding_pair=("Test Agent is working", [0.1] * embed_dim),
        filling=[],
    )
    mem.add_event(
        created=base_time + datetime.timedelta(minutes=30),
        expiration=None,
        s="Test Agent",
        p="is",
        o="eating lunch",
        description="Test Agent is eating lunch",
        keywords={"test agent", "eating", "lunch"},
        poignancy=2.0,
        embedding_pair=("Test Agent is eating lunch", [0.2] * embed_dim),
        filling=[],
    )

    # Add one thought.
    mem.add_thought(
        created=base_time + datetime.timedelta(hours=1),
        expiration=None,
        s="Test Agent",
        p="feels",
        o="productive",
        description="Test Agent feels productive today",
        keywords={"test agent", "productive"},
        poignancy=5.0,
        embedding_pair=("Test Agent feels productive today", [0.3] * embed_dim),
        filling=[],
    )

    return mem


@pytest.fixture
def sample_scratch() -> Scratch:
    """Return a Scratch instance with test persona data.

    Passes a non-existent path so check_if_file_exists returns False and the
    constructor uses default values; we then populate identity fields manually.
    """
    scratch = Scratch("/nonexistent/path/scratch.json")

    scratch.name = "Test Agent"
    scratch.first_name = "Test"
    scratch.last_name = "Agent"
    scratch.age = 30
    scratch.innate = "curious, friendly, methodical"
    scratch.learned = "Test Agent is a software developer who loves coffee."
    scratch.currently = "working on a project"
    scratch.lifestyle = "Test Agent follows a regular 9-to-5 schedule."
    scratch.living_area = "the_ville:double studio"
    scratch.curr_time = datetime.datetime(2023, 1, 1, 9, 0, 0)
    scratch.curr_tile = (58, 9)
    scratch.daily_plan_req = "Test Agent should focus on finishing the project today."

    return scratch


@pytest.fixture
def sample_persona(sample_scratch: Scratch, sample_memory: AssociativeMemory) -> Any:
    """Return a Persona-like object with all memory components initialised.

    Bypasses file I/O by constructing via object.__new__() so no bootstrap
    files are required on disk.  The returned object has the same attributes
    as a real Persona (.name, .scratch, .a_mem, .s_mem).
    """
    # Import here (after env var is set) to avoid ImportError at collection.
    from persona.persona import Persona

    persona: Persona = object.__new__(Persona)
    persona.name = "Test Agent"
    persona.scratch = sample_scratch
    persona.a_mem = sample_memory

    # Spatial memory: empty tree (no file needed).
    persona.s_mem = MemoryTree("/nonexistent/path/spatial_memory.json")
    persona.s_mem.tree = {
        "the_ville": {
            "double studio": {
                "bedroom 1": ["bed", "closet"],
                "common room": ["sofa", "television"],
            }
        }
    }

    return persona


@pytest.fixture
def sample_maze() -> Any:
    """Return a minimal 5×5 Maze object without reading any files from disk.

    Constructs the object via object.__new__() and builds a tiny walkable
    grid suitable for basic pathfinding and tile-access tests.
    """
    from maze import Maze

    maze: Maze = object.__new__(Maze)
    maze.maze_name = "test_maze"
    maze.maze_width = 5
    maze.maze_height = 5
    maze.sq_tile_size = 32
    maze.special_constraint = ""

    # Build a 5×5 collision maze (all passable except border).
    maze.collision_maze = []
    for row in range(5):
        r: list[str] = []
        for col in range(5):
            # Make the border a collision block; interior passable.
            r.append("32125" if (row == 0 or row == 4 or col == 0 or col == 4) else "0")
        maze.collision_maze.append(r)

    # Build the tiles matrix.
    maze.tiles = []
    for row in range(5):
        tile_row: list[dict[str, Any]] = []
        for col in range(5):
            tile: dict[str, Any] = {
                "world": "test_world",
                "sector": "test_sector" if (1 <= row <= 3 and 1 <= col <= 3) else "",
                "arena": "test_arena" if (1 <= row <= 3 and 1 <= col <= 3) else "",
                "game_object": "",
                "spawning_location": "spawn-a" if (row == 2 and col == 2) else "",
                "collision": maze.collision_maze[row][col] != "0",
                "events": set(),
            }
            tile_row.append(tile)
        maze.tiles.append(tile_row)

    # Build address_tiles reverse lookup.
    maze.address_tiles = {}  # type: ignore[var-annotated]
    for row in range(5):
        for col in range(5):
            tile = maze.tiles[row][col]
            addresses = []
            if tile["sector"]:
                addresses.append(f"test_world:{tile['sector']}")
            if tile["arena"]:
                addresses.append(f"test_world:{tile['sector']}:{tile['arena']}")
            if tile["spawning_location"]:
                addresses.append(f"<spawn_loc>{tile['spawning_location']}")
            for addr in addresses:
                maze.address_tiles.setdefault(addr, set()).add((col, row))

    return maze
