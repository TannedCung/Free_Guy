"""
Integration tests for REST API endpoints.

Tests use Django's test client and patch STORAGE_DIR / COMPRESSED_STORAGE_DIR
to isolated temporary directories so no real simulation data is needed.
"""

import json
import os
import shutil
import tempfile
from unittest.mock import patch

from django.test import TestCase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_sim(root: str, sim_code: str, persona_names: list[str] | None = None) -> str:
    """Create a minimal simulation directory under *root* and return its path."""
    sim_dir = os.path.join(root, sim_code)
    os.makedirs(os.path.join(sim_dir, "reverie"))
    os.makedirs(os.path.join(sim_dir, "environment"))
    os.makedirs(os.path.join(sim_dir, "movement"))
    os.makedirs(os.path.join(sim_dir, "personas"))

    if persona_names is None:
        persona_names = []

    meta = {
        "fork_sim_code": None,
        "start_date": "February 13, 2023",
        "curr_time": "February 13, 2023, 00:00:30",
        "sec_per_step": 10,
        "maze_name": "the_ville",
        "persona_names": persona_names,
        "step": 3,
    }
    with open(os.path.join(sim_dir, "reverie", "meta.json"), "w") as f:
        json.dump(meta, f)

    return sim_dir


def _add_env_step(sim_dir: str, step: int, agents: dict) -> None:
    """Write an environment/{step}.json file into *sim_dir*."""
    with open(os.path.join(sim_dir, "environment", f"{step}.json"), "w") as f:
        json.dump(agents, f)


def _add_agent_scratch(sim_dir: str, agent_name: str, scratch: dict) -> None:
    """Write scratch.json for an agent inside bootstrap_memory/."""
    agent_dir = os.path.join(sim_dir, "personas", agent_name, "bootstrap_memory")
    os.makedirs(agent_dir, exist_ok=True)
    with open(os.path.join(agent_dir, "scratch.json"), "w") as f:
        json.dump(scratch, f)


def _build_demo(root: str, demo_code: str, persona_names: list[str] | None = None) -> str:
    """Create a minimal demo directory under *root* and return its path."""
    demo_dir = os.path.join(root, demo_code)
    os.makedirs(demo_dir)

    if persona_names is None:
        persona_names = ["Alice"]

    meta = {
        "fork_sim_code": None,
        "start_date": "February 13, 2023",
        "curr_time": "February 13, 2023, 00:00:30",
        "sec_per_step": 10,
        "maze_name": "the_ville",
        "persona_names": persona_names,
        "step": 2,
    }
    with open(os.path.join(demo_dir, "meta.json"), "w") as f:
        json.dump(meta, f)

    movement = {
        "0": {
            name: {
                "movement": [10 + i, 20],
                "pronunciatio": "😴",
                "description": "sleeping @ home",
                "chat": None,
            }
            for i, name in enumerate(persona_names)
        },
        "1": {
            name: {
                "movement": [11 + i, 20],
                "pronunciatio": "☕",
                "description": "making coffee @ kitchen",
                "chat": None,
            }
            for i, name in enumerate(persona_names)
        },
    }
    with open(os.path.join(demo_dir, "master_movement.json"), "w") as f:
        json.dump(movement, f)

    return demo_dir


# ---------------------------------------------------------------------------
# Simulation list (GET /api/v1/simulations/)
# ---------------------------------------------------------------------------

class SimulationsListGetTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _get(self):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.get("/api/v1/simulations/")

    def test_empty_storage_returns_empty_list(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("simulations", data)
        self.assertEqual(data["simulations"], [])

    def test_lists_existing_simulations(self):
        _build_sim(self.storage_dir, "sim-alpha")
        _build_sim(self.storage_dir, "sim-beta")
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        ids = [s["id"] for s in resp.json()["simulations"]]
        self.assertIn("sim-alpha", ids)
        self.assertIn("sim-beta", ids)

    def test_simulation_has_required_fields(self):
        _build_sim(self.storage_dir, "sim-test", persona_names=["Alice"])
        resp = self._get()
        sim = next(s for s in resp.json()["simulations"] if s["id"] == "sim-test")
        for field in ("id", "name", "step", "persona_names", "maze_name"):
            self.assertIn(field, sim)
        self.assertEqual(sim["persona_names"], ["Alice"])


# ---------------------------------------------------------------------------
# Simulation create (POST /api/v1/simulations/)
# ---------------------------------------------------------------------------

class SimulationsListPostTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _post(self, data):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.post(
                "/api/v1/simulations/",
                data=json.dumps(data),
                content_type="application/json",
            )

    def test_create_new_simulation_returns_201(self):
        resp = self._post({"name": "my-new-sim"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["id"], "my-new-sim")

    def test_create_creates_directory_on_disk(self):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            self.client.post(
                "/api/v1/simulations/",
                data=json.dumps({"name": "disk-check"}),
                content_type="application/json",
            )
        self.assertTrue(os.path.isdir(os.path.join(self.storage_dir, "disk-check")))

    def test_missing_name_returns_400(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_invalid_name_characters_returns_400(self):
        resp = self._post({"name": "bad name!"})
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_name_returns_409(self):
        self._post({"name": "unique-sim"})
        resp = self._post({"name": "unique-sim"})
        self.assertEqual(resp.status_code, 409)

    def test_fork_from_existing_simulation(self):
        _build_sim(self.storage_dir, "source-sim", persona_names=["Bob"])
        resp = self._post({"name": "forked-sim", "fork_from": "source-sim"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["id"], "forked-sim")
        self.assertEqual(data["fork_sim_code"], "source-sim")

    def test_fork_from_nonexistent_returns_404(self):
        resp = self._post({"name": "orphan", "fork_from": "ghost-sim"})
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Simulation state (GET /api/v1/simulations/:id/state/)
# ---------------------------------------------------------------------------

class SimulationStateTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _get(self, sim_id):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.get(f"/api/v1/simulations/{sim_id}/state/")

    def test_nonexistent_simulation_returns_404(self):
        resp = self._get("ghost-sim")
        self.assertEqual(resp.status_code, 404)

    def test_simulation_with_no_env_steps_returns_empty_agents(self):
        _build_sim(self.storage_dir, "empty-sim")
        resp = self._get("empty-sim")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["step"])
        self.assertEqual(data["agents"], {})

    def test_returns_latest_env_step_agents(self):
        sim_dir = _build_sim(self.storage_dir, "sim-with-env")
        _add_env_step(sim_dir, 0, {"Alice": {"maze": "the_ville", "x": 10, "y": 20}})
        _add_env_step(sim_dir, 3, {"Alice": {"maze": "the_ville", "x": 15, "y": 25}})
        resp = self._get("sim-with-env")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["step"], 3)
        self.assertIn("Alice", data["agents"])
        self.assertEqual(data["agents"]["Alice"]["x"], 15)


# ---------------------------------------------------------------------------
# Simulation agents (GET /api/v1/simulations/:id/agents/)
# ---------------------------------------------------------------------------

class SimulationAgentsTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _get(self, sim_id):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.get(f"/api/v1/simulations/{sim_id}/agents/")

    def test_nonexistent_simulation_returns_404(self):
        resp = self._get("ghost")
        self.assertEqual(resp.status_code, 404)

    def test_returns_agents_from_meta(self):
        sim_dir = _build_sim(self.storage_dir, "agent-sim", persona_names=["Alice", "Bob"])
        _add_env_step(sim_dir, 0, {
            "Alice": {"maze": "the_ville", "x": 5, "y": 10},
            "Bob": {"maze": "the_ville", "x": 6, "y": 11},
        })
        _add_agent_scratch(sim_dir, "Alice", {"first_name": "Alice", "last_name": "Smith", "age": 30})
        _add_agent_scratch(sim_dir, "Bob", {"first_name": "Bob", "last_name": "Jones", "age": 25})
        resp = self._get("agent-sim")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["simulation_id"], "agent-sim")
        agent_ids = [a["id"] for a in data["agents"]]
        self.assertIn("Alice", agent_ids)
        self.assertIn("Bob", agent_ids)

    def test_agent_has_required_fields(self):
        sim_dir = _build_sim(self.storage_dir, "field-check-sim", persona_names=["Carol"])
        _add_agent_scratch(sim_dir, "Carol", {
            "first_name": "Carol",
            "last_name": "White",
            "age": 35,
            "innate": "friendly",
            "currently": "studying",
        })
        resp = self._get("field-check-sim")
        self.assertEqual(resp.status_code, 200)
        agent = resp.json()["agents"][0]
        for field in ("id", "name", "first_name", "last_name", "age", "innate", "currently"):
            self.assertIn(field, agent)


# ---------------------------------------------------------------------------
# Demo step (GET /api/v1/demos/:id/step/:step/)
# ---------------------------------------------------------------------------

class DemoStepTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _get(self, demo_id, step):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.get(f"/api/v1/demos/{demo_id}/step/{step}/")

    def test_nonexistent_demo_returns_404(self):
        resp = self._get("ghost-demo", 0)
        self.assertEqual(resp.status_code, 404)

    def test_step_out_of_range_returns_404(self):
        _build_demo(self.compressed_dir, "demo-a", persona_names=["Alice"])
        resp = self._get("demo-a", 999)
        self.assertEqual(resp.status_code, 404)

    def test_returns_agent_data_for_valid_step(self):
        _build_demo(self.compressed_dir, "demo-b", persona_names=["Alice"])
        resp = self._get("demo-b", 0)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["demo_id"], "demo-b")
        self.assertEqual(data["step"], 0)
        self.assertIn("agents", data)
        self.assertIn("Alice", data["agents"])

    def test_agent_data_has_required_fields(self):
        _build_demo(self.compressed_dir, "demo-c", persona_names=["Bob"])
        resp = self._get("demo-c", 1)
        self.assertEqual(resp.status_code, 200)
        agent = resp.json()["agents"]["Bob"]
        for field in ("movement", "pronunciatio", "description", "chat"):
            self.assertIn(field, agent)

    def test_movement_is_two_element_list(self):
        _build_demo(self.compressed_dir, "demo-d", persona_names=["Carol"])
        resp = self._get("demo-d", 0)
        self.assertEqual(resp.status_code, 200)
        movement = resp.json()["agents"]["Carol"]["movement"]
        self.assertIsInstance(movement, list)
        self.assertEqual(len(movement), 2)


# ---------------------------------------------------------------------------
# Demo list (GET /api/v1/demos/)
# ---------------------------------------------------------------------------

class DemosListTests(TestCase):
    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()
        self.compressed_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)
        shutil.rmtree(self.compressed_dir, ignore_errors=True)

    def _get(self):
        with patch("translator.api_views.STORAGE_DIR", self.storage_dir), \
             patch("translator.api_views.COMPRESSED_STORAGE_DIR", self.compressed_dir):
            return self.client.get("/api/v1/demos/")

    def test_empty_compressed_storage_returns_empty_list(self):
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["demos"], [])

    def test_lists_existing_demos(self):
        _build_demo(self.compressed_dir, "demo-one", persona_names=["Alice"])
        _build_demo(self.compressed_dir, "demo-two", persona_names=["Bob"])
        resp = self._get()
        self.assertEqual(resp.status_code, 200)
        ids = [d["id"] for d in resp.json()["demos"]]
        self.assertIn("demo-one", ids)
        self.assertIn("demo-two", ids)

    def test_demo_summary_has_total_steps(self):
        _build_demo(self.compressed_dir, "demo-steps", persona_names=["Alice"])
        resp = self._get()
        demo = next(d for d in resp.json()["demos"] if d["id"] == "demo-steps")
        # _build_demo creates 2 steps (keys "0" and "1")
        self.assertEqual(demo["total_steps"], 2)
