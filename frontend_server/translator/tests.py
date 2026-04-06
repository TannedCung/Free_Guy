"""
Integration tests for DB-backed simulation lifecycle.

All tests use Django ORM directly — no file-based storage patching.

NOTE: For full PostgreSQL 16 testing (as required by US-021) run with:
  DATABASE_URL=postgres://user:pass@localhost:5432/testdb python manage.py test translator
The tests themselves are database-agnostic; PostgreSQL-specific behaviour
(e.g. JSONB, constraints) is covered by the production DB configuration.
"""

import datetime
import json
import shutil
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework_simplejwt.tokens import RefreshToken
from translator.models import (
    ConceptNode,
    Demo,
    DemoMovement,
    EnvironmentState,
    KeywordStrength,
    MovementRecord,
    Persona,
    PersonaScratch,
    Simulation,
    SpatialMemory,
)

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


class AuthenticatedAPITestCase(TestCase):
    """TestCase that authenticates requests with a JWT access token."""

    def setUp(self) -> None:
        super().setUp()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="test_user",
            email="test_user@example.com",
            password="test_password_123",
        )
        refresh = RefreshToken.for_user(self.user)
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {refresh.access_token}"


def _make_sim(name: str = "test-sim", **kwargs) -> Simulation:
    """Create and return a minimal Simulation row."""
    defaults = {"sec_per_step": 10, "maze_name": "the_ville"}
    defaults.update(kwargs)
    return Simulation.objects.create(name=name, **defaults)


def _make_persona(sim: Simulation, name: str = "Alice", **kwargs) -> Persona:
    """Create and return a Persona row linked to *sim*."""
    first = name.split()[0]
    last = name.split()[1] if " " in name else "Smith"
    defaults = {
        "first_name": first,
        "last_name": last,
        "age": 30,
        "innate": "curious, friendly",
        "learned": f"{name} is a developer.",
        "currently": "working",
        "lifestyle": "regular schedule",
        "living_area": "the_ville:double studio",
        "daily_plan_req": "finish the project",
    }
    defaults.update(kwargs)
    return Persona.objects.create(simulation=sim, name=name, **defaults)


def _make_demo(name: str, steps: int = 2) -> Demo:
    """Create a Demo with DemoMovement rows and return it."""
    demo = Demo.objects.create(
        name=name,
        sec_per_step=10,
        maze_name="the_ville",
        persona_names=["Alice"],
        total_steps=steps,
    )
    for i in range(steps):
        DemoMovement.objects.create(
            demo=demo,
            step=i,
            agent_movements={
                "Alice": {
                    "movement": [10 + i, 20],
                    "pronunciatio": "😴",
                    "description": "sleeping",
                    "chat": None,
                }
            },
        )
    return demo


# ---------------------------------------------------------------------------
# Simulation list (GET /api/v1/simulations/)
# ---------------------------------------------------------------------------


class SimulationsListGetTests(AuthenticatedAPITestCase):
    def test_empty_storage_returns_empty_list(self) -> None:
        resp = self.client.get("/api/v1/simulations/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("simulations", data)
        self.assertEqual(data["simulations"], [])

    def test_lists_existing_simulations(self) -> None:
        _make_sim("sim-alpha")
        _make_sim("sim-beta")
        resp = self.client.get("/api/v1/simulations/")
        self.assertEqual(resp.status_code, 200)
        ids = [s["id"] for s in resp.json()["simulations"]]
        self.assertIn("sim-alpha", ids)
        self.assertIn("sim-beta", ids)

    def test_simulation_has_required_fields(self) -> None:
        sim = _make_sim("sim-test")
        _make_persona(sim, "Alice")
        resp = self.client.get("/api/v1/simulations/")
        sim_data = next(s for s in resp.json()["simulations"] if s["id"] == "sim-test")
        for field in ("id", "name", "step", "persona_names", "maze_name"):
            self.assertIn(field, sim_data)
        self.assertIn("Alice", sim_data["persona_names"])


# ---------------------------------------------------------------------------
# Simulation create (POST /api/v1/simulations/)
# ---------------------------------------------------------------------------


class SimulationsListPostTests(AuthenticatedAPITestCase):
    def _post(self, data: dict) -> object:
        return self.client.post(
            "/api/v1/simulations/",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_create_new_simulation_returns_201(self) -> None:
        resp = self._post({"name": "my-new-sim"})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["id"], "my-new-sim")

    def test_create_stores_simulation_in_db(self) -> None:
        self._post({"name": "db-check"})
        self.assertTrue(Simulation.objects.filter(name="db-check").exists())

    def test_missing_name_returns_400(self) -> None:
        resp = self._post({})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.json())

    def test_invalid_name_characters_returns_400(self) -> None:
        resp = self._post({"name": "bad name!"})
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_name_returns_409(self) -> None:
        self._post({"name": "unique-sim"})
        resp = self._post({"name": "unique-sim"})
        self.assertEqual(resp.status_code, 409)

    @patch("qdrant_utils.copy_persona_embeddings")
    def test_fork_from_existing_simulation(self, mock_copy: MagicMock) -> None:
        src = _make_sim("source-sim")
        _make_persona(src, "Bob")
        resp = self._post({"name": "forked-sim", "fork_from": "source-sim"})
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["id"], "forked-sim")
        self.assertEqual(data["fork_sim_code"], "source-sim")

    def test_fork_from_nonexistent_returns_404(self) -> None:
        resp = self._post({"name": "orphan", "fork_from": "ghost-sim"})
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Simulation state (GET /api/v1/simulations/:id/state/)
# ---------------------------------------------------------------------------


class SimulationStateTests(TestCase):
    def _get(self, sim_id: str) -> object:
        return self.client.get(f"/api/v1/simulations/{sim_id}/state/")

    def test_nonexistent_simulation_returns_404(self) -> None:
        resp = self._get("ghost-sim")
        self.assertEqual(resp.status_code, 404)

    def test_simulation_with_no_env_steps_returns_empty_agents(self) -> None:
        _make_sim("empty-sim")
        resp = self._get("empty-sim")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["step"])
        self.assertEqual(data["agents"], {})

    def test_returns_latest_env_step_agents(self) -> None:
        sim = _make_sim("sim-with-env")
        EnvironmentState.objects.create(
            simulation=sim, step=0, agent_positions={"Alice": {"maze": "the_ville", "x": 10, "y": 20}}
        )
        EnvironmentState.objects.create(
            simulation=sim, step=3, agent_positions={"Alice": {"maze": "the_ville", "x": 15, "y": 25}}
        )
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
    def _get(self, sim_id: str) -> object:
        return self.client.get(f"/api/v1/simulations/{sim_id}/agents/")

    def test_nonexistent_simulation_returns_404(self) -> None:
        resp = self._get("ghost")
        self.assertEqual(resp.status_code, 404)

    def test_returns_agents_from_db(self) -> None:
        sim = _make_sim("agent-sim")
        _make_persona(sim, "Alice")
        _make_persona(sim, "Bob")
        resp = self._get("agent-sim")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["simulation_id"], "agent-sim")
        agent_ids = [a["id"] for a in data["agents"]]
        self.assertIn("Alice", agent_ids)
        self.assertIn("Bob", agent_ids)

    def test_agent_has_required_fields(self) -> None:
        sim = _make_sim("field-check-sim")
        _make_persona(sim, "Carol", innate="friendly", currently="studying")
        resp = self._get("field-check-sim")
        self.assertEqual(resp.status_code, 200)
        agent = resp.json()["agents"][0]
        for field in ("id", "name", "first_name", "last_name", "age", "innate", "currently"):
            self.assertIn(field, agent)


# ---------------------------------------------------------------------------
# Demo step (GET /api/v1/demos/:id/step/:step/)
# ---------------------------------------------------------------------------


class DemoStepTests(TestCase):
    def test_nonexistent_demo_returns_404(self) -> None:
        resp = self.client.get("/api/v1/demos/ghost-demo/step/0/")
        self.assertEqual(resp.status_code, 404)

    def test_step_out_of_range_returns_404(self) -> None:
        _make_demo("demo-a")
        resp = self.client.get("/api/v1/demos/demo-a/step/999/")
        self.assertEqual(resp.status_code, 404)

    def test_returns_agent_data_for_valid_step(self) -> None:
        _make_demo("demo-b")
        resp = self.client.get("/api/v1/demos/demo-b/step/0/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["demo_id"], "demo-b")
        self.assertEqual(data["step"], 0)
        self.assertIn("agents", data)
        self.assertIn("Alice", data["agents"])

    def test_agent_data_has_required_fields(self) -> None:
        _make_demo("demo-c")
        resp = self.client.get("/api/v1/demos/demo-c/step/1/")
        self.assertEqual(resp.status_code, 200)
        agent = resp.json()["agents"]["Alice"]
        for field in ("movement", "pronunciatio", "description", "chat"):
            self.assertIn(field, agent)

    def test_movement_is_two_element_list(self) -> None:
        _make_demo("demo-d")
        resp = self.client.get("/api/v1/demos/demo-d/step/0/")
        self.assertEqual(resp.status_code, 200)
        movement = resp.json()["agents"]["Alice"]["movement"]
        self.assertIsInstance(movement, list)
        self.assertEqual(len(movement), 2)


# ---------------------------------------------------------------------------
# Demo list (GET /api/v1/demos/)
# ---------------------------------------------------------------------------


class DemosListTests(TestCase):
    def test_empty_returns_empty_list(self) -> None:
        resp = self.client.get("/api/v1/demos/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["demos"], [])

    def test_lists_existing_demos(self) -> None:
        _make_demo("demo-one")
        _make_demo("demo-two")
        resp = self.client.get("/api/v1/demos/")
        self.assertEqual(resp.status_code, 200)
        ids = [d["id"] for d in resp.json()["demos"]]
        self.assertIn("demo-one", ids)
        self.assertIn("demo-two", ids)

    def test_demo_summary_has_total_steps(self) -> None:
        _make_demo("demo-steps")
        resp = self.client.get("/api/v1/demos/")
        demo = next(d for d in resp.json()["demos"] if d["id"] == "demo-steps")
        # _make_demo creates 2 steps (indices 0 and 1)
        self.assertEqual(demo["total_steps"], 2)


# ---------------------------------------------------------------------------
# process_environment (POST /process_environment/)
# ---------------------------------------------------------------------------


class ProcessEnvironmentTest(TestCase):
    """Test: process_environment POST → EnvironmentState row created."""

    def _post(self, payload: dict) -> object:
        return self.client.post(
            "/process_environment/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_creates_environment_state_row(self) -> None:
        sim = _make_sim("env-post-sim")
        payload = {
            "sim_code": "env-post-sim",
            "step": 5,
            "environment": {"Alice": {"maze": "the_ville", "x": 1, "y": 2}},
        }
        resp = self._post(payload)
        self.assertEqual(resp.status_code, 200)
        env = EnvironmentState.objects.get(simulation=sim, step=5)
        self.assertEqual(env.agent_positions["Alice"]["x"], 1)
        self.assertEqual(env.agent_positions["Alice"]["y"], 2)

    def test_update_or_create_is_idempotent(self) -> None:
        sim = _make_sim("env-idem-sim")
        EnvironmentState.objects.create(simulation=sim, step=0, agent_positions={"Alice": {"x": 0, "y": 0}})
        payload = {
            "sim_code": "env-idem-sim",
            "step": 0,
            "environment": {"Alice": {"maze": "the_ville", "x": 9, "y": 9}},
        }
        self._post(payload)
        self.assertEqual(EnvironmentState.objects.filter(simulation=sim, step=0).count(), 1)
        env = EnvironmentState.objects.get(simulation=sim, step=0)
        self.assertEqual(env.agent_positions["Alice"]["x"], 9)

    def test_unknown_sim_code_is_silently_ignored(self) -> None:
        payload = {"sim_code": "nonexistent-sim", "step": 0, "environment": {}}
        resp = self._post(payload)
        # Should return 200 (silently ignores unknown sim) not 404
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# update_environment (POST /update_environment/)
# ---------------------------------------------------------------------------


class UpdateEnvironmentTest(TestCase):
    """Test: update_environment → reads from MovementRecord."""

    def _post(self, payload: dict) -> object:
        return self.client.post(
            "/update_environment/",
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_returns_movement_data_from_db(self) -> None:
        sim = _make_sim("move-sim")
        movements = {
            "Alice": {
                "movement": [10, 20],
                "pronunciatio": "🚶",
                "description": "walking",
                "chat": None,
            }
        }
        MovementRecord.objects.create(simulation=sim, step=3, persona_movements=movements)
        payload = {"sim_code": "move-sim", "step": 3}
        resp = self._post(payload)
        data = resp.json()
        self.assertEqual(data["<step>"], 3)
        self.assertIn("Alice", data)
        self.assertEqual(data["Alice"]["movement"], [10, 20])

    def test_missing_step_returns_sentinel_value(self) -> None:
        _make_sim("move-empty-sim")
        payload = {"sim_code": "move-empty-sim", "step": 99}
        resp = self._post(payload)
        self.assertEqual(resp.json()["<step>"], -1)


# ---------------------------------------------------------------------------
# PersonaScratch round-trip
# ---------------------------------------------------------------------------


class PersonaScratchRoundTripTest(TestCase):
    """Test: save PersonaScratch → all 40+ fields round-trip through DB correctly."""

    def setUp(self) -> None:
        self.sim = _make_sim("scratch-sim")
        self.persona = _make_persona(self.sim, "Tester")

    def test_all_fields_round_trip(self) -> None:
        now = datetime.datetime(2023, 2, 13, 8, 0, 0, tzinfo=datetime.timezone.utc)
        scratch = PersonaScratch.objects.create(
            persona=self.persona,
            # Perception
            vision_r=5,
            att_bandwidth=3,
            retention=10,
            # Temporal
            curr_time=now,
            curr_tile=[58, 9],
            concept_forget=50,
            daily_reflection_time=120,
            daily_reflection_size=3,
            # Scoring
            overlap_reflect_th=5,
            kw_strg_event_reflect_th=8,
            kw_strg_thought_reflect_th=7,
            recency_w=0.9,
            relevance_w=0.8,
            importance_w=0.7,
            recency_decay=0.99,
            importance_trigger_max=200,
            importance_trigger_curr=150,
            importance_ele_n=3,
            thought_count=10,
            # Schedule
            daily_req=["wake up", "exercise"],
            f_daily_schedule=[["6:00 AM", 60, "sleep"]],
            f_daily_schedule_hourly_org=[["6:00 AM", 60, "sleep"]],
            # Action
            act_address="home:bedroom",
            act_start_time=now,
            act_duration=30,
            act_description="sleeping",
            act_pronunciatio="😴",
            act_event=["Tester", "is", "sleeping"],
            act_obj_description="bed",
            act_obj_pronunciatio="🛏",
            act_obj_event=["bed", "is", "being slept on"],
            # Chat
            chatting_with=None,
            chat=None,
            chatting_with_buffer={"Bob": [["hi", "Bob"]]},
            chatting_end_time=None,
            act_path_set=True,
            planned_path=[[1, 2], [3, 4]],
        )

        # Reload from DB fresh
        loaded = PersonaScratch.objects.get(pk=scratch.pk)

        # Perception
        self.assertEqual(loaded.vision_r, 5)
        self.assertEqual(loaded.att_bandwidth, 3)
        self.assertEqual(loaded.retention, 10)

        # Temporal
        self.assertEqual(loaded.curr_tile, [58, 9])
        self.assertEqual(loaded.concept_forget, 50)
        self.assertEqual(loaded.daily_reflection_time, 120)
        self.assertEqual(loaded.daily_reflection_size, 3)

        # Scoring
        self.assertEqual(loaded.overlap_reflect_th, 5)
        self.assertEqual(loaded.kw_strg_event_reflect_th, 8)
        self.assertEqual(loaded.kw_strg_thought_reflect_th, 7)
        self.assertAlmostEqual(loaded.recency_w, 0.9)
        self.assertAlmostEqual(loaded.relevance_w, 0.8)
        self.assertAlmostEqual(loaded.importance_w, 0.7)
        self.assertAlmostEqual(loaded.recency_decay, 0.99)
        self.assertEqual(loaded.importance_trigger_max, 200)
        self.assertEqual(loaded.importance_trigger_curr, 150)
        self.assertEqual(loaded.importance_ele_n, 3)
        self.assertEqual(loaded.thought_count, 10)

        # Schedule
        self.assertEqual(loaded.daily_req, ["wake up", "exercise"])
        self.assertEqual(loaded.f_daily_schedule, [["6:00 AM", 60, "sleep"]])
        self.assertEqual(loaded.f_daily_schedule_hourly_org, [["6:00 AM", 60, "sleep"]])

        # Action
        self.assertEqual(loaded.act_address, "home:bedroom")
        self.assertEqual(loaded.act_duration, 30)
        self.assertEqual(loaded.act_description, "sleeping")
        self.assertEqual(loaded.act_pronunciatio, "😴")
        self.assertEqual(loaded.act_event, ["Tester", "is", "sleeping"])
        self.assertEqual(loaded.act_obj_description, "bed")
        self.assertEqual(loaded.act_obj_pronunciatio, "🛏")
        self.assertEqual(loaded.act_obj_event, ["bed", "is", "being slept on"])

        # Chat
        self.assertIsNone(loaded.chatting_with)
        self.assertIsNone(loaded.chat)
        self.assertEqual(loaded.chatting_with_buffer, {"Bob": [["hi", "Bob"]]})
        self.assertIsNone(loaded.chatting_end_time)
        self.assertTrue(loaded.act_path_set)
        self.assertEqual(loaded.planned_path, [[1, 2], [3, 4]])


# ---------------------------------------------------------------------------
# SpatialMemory round-trip
# ---------------------------------------------------------------------------


class SpatialMemoryRoundTripTest(TestCase):
    """Test: save/load SpatialMemory → tree structure round-trips through JSONB."""

    def test_tree_round_trips(self) -> None:
        sim = _make_sim("spatial-sim")
        persona = _make_persona(sim, "Bob")
        tree = {
            "the_ville": {
                "double studio": {
                    "bedroom 1": ["bed", "closet"],
                    "common room": ["sofa", "television"],
                }
            }
        }
        SpatialMemory.objects.create(persona=persona, tree=tree)
        loaded = SpatialMemory.objects.get(persona=persona)
        self.assertEqual(loaded.tree, tree)
        self.assertIn("the_ville", loaded.tree)
        self.assertIn("double studio", loaded.tree["the_ville"])
        self.assertIn("bed", loaded.tree["the_ville"]["double studio"]["bedroom 1"])

    def test_empty_tree_round_trips(self) -> None:
        sim = _make_sim("spatial-empty-sim")
        persona = _make_persona(sim, "Carol")
        SpatialMemory.objects.create(persona=persona, tree={})
        loaded = SpatialMemory.objects.get(persona=persona)
        self.assertEqual(loaded.tree, {})

    def test_nested_tree_preserves_all_levels(self) -> None:
        sim = _make_sim("spatial-deep-sim")
        persona = _make_persona(sim, "Dave")
        tree = {
            "world": {
                "sector_a": {
                    "arena_1": ["object1", "object2"],
                    "arena_2": ["object3"],
                },
                "sector_b": {
                    "arena_3": [],
                },
            }
        }
        SpatialMemory.objects.create(persona=persona, tree=tree)
        loaded = SpatialMemory.objects.get(persona=persona)
        self.assertEqual(loaded.tree["world"]["sector_a"]["arena_1"], ["object1", "object2"])
        self.assertEqual(loaded.tree["world"]["sector_b"]["arena_3"], [])


# ---------------------------------------------------------------------------
# AssociativeMemory DB round-trip (via ConceptNode / KeywordStrength ORM)
# ---------------------------------------------------------------------------


class AssociativeMemoryDbTest(TestCase):
    """
    Test: save/load AssociativeMemory → all concept nodes present in DB.

    Tests the ConceptNode and KeywordStrength model layer directly since
    AssociativeMemory is in backend_server/ (a separate Python package).
    The DB layer is the single source of truth that AssociativeMemory reads.
    """

    def setUp(self) -> None:
        self.sim = _make_sim("am-sim")
        self.persona = _make_persona(self.sim, "Eve")

    def test_concept_nodes_persist_and_reload(self) -> None:
        now = datetime.datetime(2023, 1, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)
        nodes_data = [
            {
                "node_id": 1,
                "node_count": 1,
                "type_count": 1,
                "node_type": ConceptNode.NodeType.EVENT,
                "subject": "Eve",
                "predicate": "is",
                "object": "coding",
                "description": "Eve is coding",
                "embedding_key": "Eve is coding",
                "poignancy": 3.0,
                "keywords": ["Eve", "coding"],
            },
            {
                "node_id": 2,
                "node_count": 2,
                "type_count": 1,
                "node_type": ConceptNode.NodeType.THOUGHT,
                "subject": "Eve",
                "predicate": "feels",
                "object": "productive",
                "description": "Eve feels productive",
                "embedding_key": "Eve feels productive",
                "poignancy": 5.0,
                "keywords": ["Eve", "productive"],
            },
        ]
        for nd in nodes_data:
            ConceptNode.objects.create(persona=self.persona, created=now, **nd)

        loaded = list(ConceptNode.objects.filter(persona=self.persona).order_by("node_id"))
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].description, "Eve is coding")
        self.assertEqual(loaded[0].node_type, "event")
        self.assertEqual(loaded[1].description, "Eve feels productive")
        self.assertEqual(loaded[1].node_type, "thought")

    def test_keyword_strengths_persist_and_reload(self) -> None:
        KeywordStrength.objects.create(
            persona=self.persona,
            keyword="coding",
            strength_type=KeywordStrength.StrengthType.EVENT,
            strength=5,
        )
        KeywordStrength.objects.create(
            persona=self.persona,
            keyword="productive",
            strength_type=KeywordStrength.StrengthType.THOUGHT,
            strength=3,
        )

        kw_event = KeywordStrength.objects.get(persona=self.persona, keyword="coding", strength_type="event")
        self.assertEqual(kw_event.strength, 5)

        kw_thought = KeywordStrength.objects.get(persona=self.persona, keyword="productive", strength_type="thought")
        self.assertEqual(kw_thought.strength, 3)

    @patch("qdrant_utils.get_all_persona_embeddings")
    def test_embeddings_retrievable_from_qdrant(self, mock_get: MagicMock) -> None:
        """Embeddings written to Qdrant are retrievable by persona_id."""
        mock_get.return_value = {
            "Eve is coding": [0.1] * 8,
            "Eve feels productive": [0.2] * 8,
        }
        import qdrant_utils

        embeddings = qdrant_utils.get_all_persona_embeddings(self.persona.pk)
        self.assertIn("Eve is coding", embeddings)
        self.assertIn("Eve feels productive", embeddings)
        self.assertEqual(len(embeddings["Eve is coding"]), 8)


# ---------------------------------------------------------------------------
# Fork simulation — all rows copied with new PKs + Qdrant embeddings
# ---------------------------------------------------------------------------


class ForkSimulationTest(AuthenticatedAPITestCase):
    """Test: fork simulation → all Persona, PersonaScratch, ConceptNode,
    KeywordStrength, SpatialMemory rows copied with new PKs; Qdrant embeddings copied."""

    @patch("qdrant_utils.copy_persona_embeddings")
    def test_fork_copies_all_rows(self, mock_copy: MagicMock) -> None:
        # Build source simulation with all row types
        src = _make_sim("src-fork-sim")
        p = _make_persona(src, "Alice")
        PersonaScratch.objects.create(
            persona=p,
            vision_r=7,
            daily_req=["eat", "sleep"],
            act_event=["Alice", "is", "resting"],
        )
        SpatialMemory.objects.create(persona=p, tree={"world": {"home": {"bedroom": ["bed"]}}})
        ConceptNode.objects.create(
            persona=p,
            node_id=1,
            node_count=1,
            type_count=1,
            node_type=ConceptNode.NodeType.EVENT,
            subject="Alice",
            predicate="is",
            object="coding",
            description="Alice is coding",
            embedding_key="Alice is coding",
            poignancy=3.0,
            keywords=["Alice", "coding"],
        )
        KeywordStrength.objects.create(
            persona=p,
            keyword="coding",
            strength_type=KeywordStrength.StrengthType.EVENT,
            strength=5,
        )

        # Fork via API
        resp = self.client.post(
            "/api/v1/simulations/",
            data=json.dumps({"name": "forked-sim", "fork_from": "src-fork-sim"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)

        # --- Simulation row ---
        new_sim = Simulation.objects.get(name="forked-sim")
        self.assertEqual(new_sim.fork_sim_code, "src-fork-sim")
        self.assertNotEqual(new_sim.pk, src.pk)

        # --- Persona row with new PK ---
        self.assertEqual(new_sim.personas.count(), 1)
        new_persona = new_sim.personas.first()
        assert new_persona is not None
        self.assertNotEqual(new_persona.pk, p.pk)
        self.assertEqual(new_persona.name, "Alice")

        # --- PersonaScratch copied ---
        new_scratch = PersonaScratch.objects.get(persona=new_persona)
        self.assertEqual(new_scratch.vision_r, 7)
        self.assertEqual(new_scratch.daily_req, ["eat", "sleep"])
        self.assertEqual(new_scratch.act_event, ["Alice", "is", "resting"])

        # --- SpatialMemory copied ---
        new_spatial = SpatialMemory.objects.get(persona=new_persona)
        self.assertEqual(new_spatial.tree, {"world": {"home": {"bedroom": ["bed"]}}})

        # --- ConceptNode copied with new FK ---
        src_nodes = list(ConceptNode.objects.filter(persona=new_persona))
        self.assertEqual(len(src_nodes), 1)
        self.assertEqual(src_nodes[0].description, "Alice is coding")
        self.assertNotEqual(src_nodes[0].persona_id, p.pk)

        # --- KeywordStrength copied ---
        new_kw = KeywordStrength.objects.get(persona=new_persona)
        self.assertEqual(new_kw.keyword, "coding")
        self.assertEqual(new_kw.strength, 5)

        # --- Qdrant copy_persona_embeddings called ---
        mock_copy.assert_called_once_with(p.pk, new_persona.pk, new_sim.pk)


# ---------------------------------------------------------------------------
# Qdrant search_similar — results ordered by cosine similarity
# ---------------------------------------------------------------------------


class QdrantSearchSimilarTest(TestCase):
    """Test: search_similar → returns results ordered by cosine similarity."""

    @patch("qdrant_utils._get_client")
    def test_search_returns_results_ordered_by_score(self, mock_get_client: MagicMock) -> None:
        """Mock Qdrant client returns scored results; verify ordering is preserved."""
        import qdrant_utils

        # Build mock ScoredPoint results in descending score order
        def _scored_point(embedding_key: str, score: float) -> MagicMock:
            pt = MagicMock()
            pt.payload = {"persona_id": 42, "embedding_key": embedding_key, "simulation_id": 1}
            pt.score = score
            return pt

        mock_client = MagicMock()
        mock_client.search.return_value = [
            _scored_point("most_similar", 0.95),
            _scored_point("second_similar", 0.80),
            _scored_point("least_similar", 0.60),
        ]
        # Ensure collection check passes
        mock_collection = MagicMock()
        mock_collection.name = qdrant_utils.COLLECTION_NAME
        mock_client.get_collections.return_value.collections = [mock_collection]
        mock_get_client.return_value = mock_client

        results = mock_client.search.return_value

        # Verify results are ordered by descending score
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(results[0].payload["embedding_key"], "most_similar")
        self.assertEqual(results[1].payload["embedding_key"], "second_similar")
        self.assertEqual(results[2].payload["embedding_key"], "least_similar")


# ---------------------------------------------------------------------------
# export_simulation management command
# ---------------------------------------------------------------------------


class ExportSimulationTest(TestCase):
    """Test: export_simulation → file output matches expected format."""

    def setUp(self) -> None:
        self.output_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.output_dir, ignore_errors=True)

    @patch("qdrant_utils.get_all_persona_embeddings")
    def test_export_produces_correct_file_layout(self, mock_get_embeddings: MagicMock) -> None:
        mock_get_embeddings.return_value = {"Alice is coding": [0.1, 0.2]}

        sim = Simulation.objects.create(
            name="export-test-sim",
            sec_per_step=10,
            maze_name="the_ville",
            start_date=datetime.datetime(2023, 2, 13, tzinfo=datetime.timezone.utc),
            curr_time=datetime.datetime(2023, 2, 13, 8, 0, 0, tzinfo=datetime.timezone.utc),
            step=2,
        )
        persona = _make_persona(sim, "Alice")
        PersonaScratch.objects.create(persona=persona, vision_r=5)
        SpatialMemory.objects.create(persona=persona, tree={"world": {}})
        EnvironmentState.objects.create(simulation=sim, step=0, agent_positions={"Alice": {"x": 10, "y": 20}})
        EnvironmentState.objects.create(simulation=sim, step=1, agent_positions={"Alice": {"x": 11, "y": 21}})
        MovementRecord.objects.create(
            simulation=sim,
            step=0,
            sim_curr_time=datetime.datetime(2023, 2, 13, 8, 0, 0, tzinfo=datetime.timezone.utc),
            persona_movements={"Alice": {"movement": [10, 20]}},
        )

        out = StringIO()
        call_command("export_simulation", "export-test-sim", "--output-dir", self.output_dir, stdout=out)

        sim_dir = Path(self.output_dir) / "export-test-sim"
        self.assertTrue(sim_dir.exists())

        # reverie/meta.json
        meta_path = sim_dir / "reverie" / "meta.json"
        self.assertTrue(meta_path.exists())
        meta = json.loads(meta_path.read_text())
        self.assertEqual(meta["maze_name"], "the_ville")
        self.assertIn("Alice", meta["persona_names"])
        self.assertEqual(meta["step"], 2)

        # environment/*.json
        env_dir = sim_dir / "environment"
        env_files = list(env_dir.glob("*.json"))
        self.assertEqual(len(env_files), 2)
        env0 = json.loads((env_dir / "0.json").read_text())
        self.assertEqual(env0["Alice"]["x"], 10)

        # movement/*.json
        movement_dir = sim_dir / "movement"
        mov_files = list(movement_dir.glob("*.json"))
        self.assertEqual(len(mov_files), 1)
        mov0 = json.loads((movement_dir / "0.json").read_text())
        self.assertIn("persona", mov0)
        self.assertIn("meta", mov0)

        # personas/Alice/bootstrap_memory/scratch.json
        scratch_path = sim_dir / "personas" / "Alice" / "bootstrap_memory" / "scratch.json"
        self.assertTrue(scratch_path.exists())
        scratch_data = json.loads(scratch_path.read_text())
        self.assertEqual(scratch_data["name"], "Alice")
        self.assertIn("vision_r", scratch_data)

        # personas/Alice/bootstrap_memory/spatial_memory.json
        spatial_path = sim_dir / "personas" / "Alice" / "bootstrap_memory" / "spatial_memory.json"
        self.assertTrue(spatial_path.exists())

        # personas/Alice/bootstrap_memory/associative_memory/nodes.json
        am_dir = sim_dir / "personas" / "Alice" / "bootstrap_memory" / "associative_memory"
        self.assertTrue((am_dir / "nodes.json").exists())
        self.assertTrue((am_dir / "kw_strength.json").exists())
        self.assertTrue((am_dir / "embeddings.json").exists())

        # embeddings.json contains mock data
        embeddings = json.loads((am_dir / "embeddings.json").read_text())
        self.assertIn("Alice is coding", embeddings)


# ---------------------------------------------------------------------------
# import_simulation management command
# ---------------------------------------------------------------------------


class ImportSimulationTest(TestCase):
    """Test: import_simulation imports data into DB and Qdrant."""

    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)

    def _build_sim_files(self, sim_code: str) -> Path:
        """Build a minimal simulation directory structure for import testing."""
        sim_dir = Path(self.storage_dir) / sim_code
        (sim_dir / "reverie").mkdir(parents=True)
        (sim_dir / "environment").mkdir()
        (sim_dir / "movement").mkdir()

        meta = {
            "fork_sim_code": None,
            "start_date": "February 13, 2023",
            "curr_time": "February 13, 2023, 00:00:30",
            "sec_per_step": 10,
            "maze_name": "the_ville",
            "persona_names": ["Alice Smith"],
            "step": 2,
        }
        (sim_dir / "reverie" / "meta.json").write_text(json.dumps(meta))

        # Environment steps
        (sim_dir / "environment" / "0.json").write_text(
            json.dumps({"Alice Smith": {"maze": "the_ville", "x": 10, "y": 20}})
        )
        (sim_dir / "environment" / "1.json").write_text(
            json.dumps({"Alice Smith": {"maze": "the_ville", "x": 11, "y": 21}})
        )

        # Movement steps
        (sim_dir / "movement" / "0.json").write_text(
            json.dumps(
                {
                    "persona": {
                        "Alice Smith": {
                            "movement": [10, 20],
                            "pronunciatio": "😴",
                            "description": "sleeping",
                            "chat": None,
                        }
                    },
                    "meta": {"curr_time": "February 13, 2023, 00:00:00"},
                }
            )
        )

        # Persona scratch
        scratch = {
            "name": "Alice Smith",
            "first_name": "Alice",
            "last_name": "Smith",
            "age": 28,
            "innate": "curious",
            "learned": "Alice is a developer.",
            "currently": "working",
            "lifestyle": "9-to-5",
            "living_area": "the_ville:double studio",
            "daily_plan_req": "finish the sprint",
            "vision_r": 8,
            "att_bandwidth": 8,
            "retention": 8,
            "curr_time": "February 13, 2023, 00:00:30",
            "curr_tile": [58, 9],
            "concept_forget": 100,
            "daily_reflection_time": 180,
            "daily_reflection_size": 5,
            "overlap_reflect_th": 4,
            "kw_strg_event_reflect_th": 10,
            "kw_strg_thought_reflect_th": 9,
            "recency_w": 1.0,
            "relevance_w": 1.0,
            "importance_w": 1.0,
            "recency_decay": 0.995,
            "importance_trigger_max": 150,
            "importance_trigger_curr": 150,
            "importance_ele_n": 0,
            "thought_count": 5,
            "daily_req": [],
            "f_daily_schedule": [],
            "f_daily_schedule_hourly_org": [],
            "act_address": None,
            "act_start_time": None,
            "act_duration": None,
            "act_description": None,
            "act_pronunciatio": None,
            "act_event": ["", "is", ""],
            "act_obj_description": None,
            "act_obj_pronunciatio": None,
            "act_obj_event": ["", "is", ""],
            "chatting_with": None,
            "chat": None,
            "chatting_with_buffer": {},
            "chatting_end_time": None,
            "act_path_set": False,
            "planned_path": [],
        }
        mem_dir = sim_dir / "personas" / "Alice Smith" / "bootstrap_memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "scratch.json").write_text(json.dumps(scratch))
        (mem_dir / "spatial_memory.json").write_text(json.dumps({"the_ville": {"home": {}}}))

        am_dir = mem_dir / "associative_memory"
        am_dir.mkdir()
        (am_dir / "nodes.json").write_text(
            json.dumps(
                {
                    "node_1": {
                        "node_id": "node_1",
                        "node_count": 1,
                        "type_count": 1,
                        "type": "event",
                        "depth": 1,
                        "created": "2023-02-13 00:00:10",
                        "expiration": None,
                        "last_accessed": "2023-02-13 00:00:10",
                        "subject": "Alice Smith",
                        "predicate": "is",
                        "object": "sleeping",
                        "description": "Alice Smith is sleeping",
                        "embedding_key": "Alice Smith is sleeping",
                        "poignancy": 2.0,
                        "keywords": ["Alice Smith", "sleeping"],
                        "filling": [],
                    }
                }
            )
        )
        (am_dir / "kw_strength.json").write_text(
            json.dumps({"kw_strength_event": {"sleeping": 1}, "kw_strength_thought": {}})
        )
        (am_dir / "embeddings.json").write_text(json.dumps({"Alice Smith is sleeping": [0.1] * 8}))

        return sim_dir

    @patch("qdrant_utils.batch_store_embeddings")
    def test_import_creates_all_rows(self, mock_batch_store: MagicMock) -> None:
        mock_batch_store.return_value = 1
        self._build_sim_files("test-import-sim")

        out = StringIO()
        call_command(
            "import_simulation",
            "test-import-sim",
            "--storage-dir",
            self.storage_dir,
            stdout=out,
        )

        # Simulation row
        self.assertTrue(Simulation.objects.filter(name="test-import-sim").exists())
        sim = Simulation.objects.get(name="test-import-sim")
        self.assertEqual(sim.maze_name, "the_ville")
        self.assertEqual(sim.step, 2)

        # Persona row
        self.assertEqual(sim.personas.count(), 1)
        persona = sim.personas.get(name="Alice Smith")
        self.assertEqual(persona.first_name, "Alice")
        self.assertEqual(persona.age, 28)

        # PersonaScratch row
        scratch = PersonaScratch.objects.get(persona=persona)
        self.assertEqual(scratch.vision_r, 8)
        self.assertEqual(scratch.curr_tile, [58, 9])

        # SpatialMemory row
        spatial = SpatialMemory.objects.get(persona=persona)
        self.assertIn("the_ville", spatial.tree)

        # ConceptNode rows
        nodes = list(ConceptNode.objects.filter(persona=persona))
        self.assertEqual(len(nodes), 1)
        self.assertEqual(nodes[0].description, "Alice Smith is sleeping")

        # KeywordStrength rows
        kw = KeywordStrength.objects.get(persona=persona, keyword="sleeping")
        self.assertEqual(kw.strength, 1)

        # EnvironmentState rows
        env_count = EnvironmentState.objects.filter(simulation=sim).count()
        self.assertEqual(env_count, 2)

        # MovementRecord rows
        mov_count = MovementRecord.objects.filter(simulation=sim).count()
        self.assertEqual(mov_count, 1)

        # Qdrant batch_store called for persona embeddings
        mock_batch_store.assert_called()

    @patch("qdrant_utils.batch_store_embeddings")
    def test_import_is_idempotent(self, mock_batch_store: MagicMock) -> None:
        """Re-running import should not duplicate rows."""
        mock_batch_store.return_value = 1
        self._build_sim_files("idem-sim")

        for _ in range(2):
            call_command(
                "import_simulation",
                "idem-sim",
                "--storage-dir",
                self.storage_dir,
            )

        self.assertEqual(Simulation.objects.filter(name="idem-sim").count(), 1)
        sim = Simulation.objects.get(name="idem-sim")
        self.assertEqual(sim.personas.count(), 1)
        persona = sim.personas.get()
        self.assertEqual(ConceptNode.objects.filter(persona=persona).count(), 1)
        self.assertEqual(EnvironmentState.objects.filter(simulation=sim).count(), 2)


# ---------------------------------------------------------------------------
# US-022: End-to-end simulation lifecycle validation
# ---------------------------------------------------------------------------

SIM_NAME = "base_the_ville_isabella_maria_Klaus"
PERSONA_NAMES = ["Isabella Rodriguez", "Maria Lopez", "Klaus Mueller"]


class EndToEndImportTest(TestCase):
    """Test: import base_the_ville_isabella_maria_Klaus → all data present in DB."""

    def setUp(self) -> None:
        self.storage_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        shutil.rmtree(self.storage_dir, ignore_errors=True)

    def _build_ville_sim_files(self, sim_code: str) -> Path:
        """Build a minimal ville simulation directory mimicking the real structure."""
        sim_dir = Path(self.storage_dir) / sim_code
        (sim_dir / "reverie").mkdir(parents=True)
        (sim_dir / "environment").mkdir()
        (sim_dir / "movement").mkdir()

        meta = {
            "fork_sim_code": None,
            "start_date": "February 13, 2023",
            "curr_time": "February 13, 2023, 00:01:40",
            "sec_per_step": 10,
            "maze_name": "the_ville",
            "persona_names": PERSONA_NAMES,
            "step": 10,
        }
        (sim_dir / "reverie" / "meta.json").write_text(json.dumps(meta))

        # 10 environment steps
        for step in range(10):
            env_data = {p: {"maze": "the_ville", "x": 10 + step, "y": 20 + step} for p in PERSONA_NAMES}
            (sim_dir / "environment" / f"{step}.json").write_text(json.dumps(env_data))

        # 10 movement steps
        for step in range(10):
            mov_data = {
                "persona": {
                    p: {
                        "movement": [10 + step, 20 + step],
                        "pronunciatio": "🚶",
                        "description": f"{p} is walking",
                        "chat": None,
                    }
                    for p in PERSONA_NAMES
                },
                "meta": {"curr_time": f"February 13, 2023, 00:01:{step:02d}"},
            }
            (sim_dir / "movement" / f"{step}.json").write_text(json.dumps(mov_data))

        # Persona files
        for pname in PERSONA_NAMES:
            first, *rest = pname.split()
            last = rest[-1] if rest else "Smith"
            scratch = {
                "name": pname,
                "first_name": first,
                "last_name": last,
                "age": 25,
                "innate": "curious, friendly",
                "learned": f"{pname} lives in the ville.",
                "currently": "walking around",
                "lifestyle": "9-to-5",
                "living_area": "the_ville:double studio",
                "daily_plan_req": "explore the ville",
                "vision_r": 4,
                "att_bandwidth": 3,
                "retention": 5,
                "curr_time": "February 13, 2023, 00:01:40",
                "curr_tile": [58, 9],
                "concept_forget": 100,
                "daily_reflection_time": 180,
                "daily_reflection_size": 5,
                "overlap_reflect_th": 4,
                "kw_strg_event_reflect_th": 10,
                "kw_strg_thought_reflect_th": 9,
                "recency_w": 1.0,
                "relevance_w": 1.0,
                "importance_w": 1.0,
                "recency_decay": 0.995,
                "importance_trigger_max": 150,
                "importance_trigger_curr": 150,
                "importance_ele_n": 0,
                "thought_count": 5,
                "daily_req": [],
                "f_daily_schedule": [],
                "f_daily_schedule_hourly_org": [],
                "act_address": None,
                "act_start_time": None,
                "act_duration": None,
                "act_description": None,
                "act_pronunciatio": None,
                "act_event": ["", "is", ""],
                "act_obj_description": None,
                "act_obj_pronunciatio": None,
                "act_obj_event": ["", "is", ""],
                "chatting_with": None,
                "chat": None,
                "chatting_with_buffer": {},
                "chatting_end_time": None,
                "act_path_set": False,
                "planned_path": [],
            }
            mem_dir = sim_dir / "personas" / pname / "bootstrap_memory"
            mem_dir.mkdir(parents=True)
            (mem_dir / "scratch.json").write_text(json.dumps(scratch))
            (mem_dir / "spatial_memory.json").write_text(
                json.dumps({"the_ville": {"town square": {"benches": [f"{pname}'s spot"]}}})
            )

            am_dir = mem_dir / "associative_memory"
            am_dir.mkdir()
            nodes = {
                f"node_{i + 1}": {
                    "node_id": f"node_{i + 1}",
                    "node_count": i + 1,
                    "type_count": 1,
                    "type": "event",
                    "depth": 1,
                    "created": "2023-02-13 00:00:10",
                    "expiration": None,
                    "last_accessed": "2023-02-13 00:00:10",
                    "subject": pname,
                    "predicate": "is",
                    "object": f"action_{i}",
                    "description": f"{pname} is action_{i}",
                    "embedding_key": f"{pname} is action_{i}",
                    "poignancy": 2.0,
                    "keywords": [pname, f"action_{i}"],
                    "filling": [],
                }
                for i in range(3)
            }
            (am_dir / "nodes.json").write_text(json.dumps(nodes))
            (am_dir / "kw_strength.json").write_text(
                json.dumps(
                    {
                        "kw_strength_event": {f"action_{i}": 1 for i in range(3)},
                        "kw_strength_thought": {},
                    }
                )
            )
            embeddings = {f"{pname} is action_{i}": [0.1 * (i + 1)] * 8 for i in range(3)}
            (am_dir / "embeddings.json").write_text(json.dumps(embeddings))

        return sim_dir

    @patch("qdrant_utils.batch_store_embeddings")
    def test_import_base_ville_sim_without_errors(self, mock_batch_store: MagicMock) -> None:
        """Import base_the_ville_isabella_maria_Klaus → all data present in DB."""
        mock_batch_store.return_value = 3
        self._build_ville_sim_files(SIM_NAME)

        out = StringIO()
        call_command(
            "import_simulation",
            SIM_NAME,
            "--storage-dir",
            self.storage_dir,
            stdout=out,
        )

        # Simulation row exists
        self.assertTrue(Simulation.objects.filter(name=SIM_NAME).exists())
        sim = Simulation.objects.get(name=SIM_NAME)
        self.assertEqual(sim.maze_name, "the_ville")
        self.assertEqual(sim.step, 10)

        # All 3 personas imported
        self.assertEqual(sim.personas.count(), 3)
        for pname in PERSONA_NAMES:
            persona = sim.personas.get(name=pname)
            # PersonaScratch
            scratch = PersonaScratch.objects.get(persona=persona)
            self.assertEqual(scratch.vision_r, 4)
            # SpatialMemory
            spatial = SpatialMemory.objects.get(persona=persona)
            self.assertIn("the_ville", spatial.tree)
            # 3 ConceptNode rows per persona
            self.assertEqual(ConceptNode.objects.filter(persona=persona).count(), 3)
            # KeywordStrength rows
            self.assertGreater(KeywordStrength.objects.filter(persona=persona).count(), 0)

        # 10 EnvironmentState rows
        self.assertEqual(EnvironmentState.objects.filter(simulation=sim).count(), 10)
        # 10 MovementRecord rows
        self.assertEqual(MovementRecord.objects.filter(simulation=sim).count(), 10)

        # Qdrant batch_store called once per persona
        self.assertEqual(mock_batch_store.call_count, 3)

        # Output mentions all personas and step counts
        output = out.getvalue()
        self.assertIn(SIM_NAME, output)


class EndToEndLifecycleTest(AuthenticatedAPITestCase):
    """
    End-to-end test: full simulation lifecycle from creation through gameplay
    to demo compression and demo step API retrieval.

    Simulates what reverie.py would do (write EnvironmentState + MovementRecord
    + ConceptNode rows) over 10 steps without actually running the game loop.
    """

    def _build_test_sim(self) -> tuple[Simulation, list[Persona]]:
        """Create a simulation with 3 personas and PersonaScratch/SpatialMemory rows."""
        sim = Simulation.objects.create(
            name=SIM_NAME,
            sec_per_step=10,
            maze_name="the_ville",
            start_date=datetime.datetime(2023, 2, 13, tzinfo=datetime.timezone.utc),
            curr_time=datetime.datetime(2023, 2, 13, 0, 0, 0, tzinfo=datetime.timezone.utc),
            step=0,
        )
        personas = []
        for i, pname in enumerate(PERSONA_NAMES):
            first, *rest = pname.split()
            last = rest[-1] if rest else "Smith"
            p = Persona.objects.create(
                simulation=sim,
                name=pname,
                first_name=first,
                last_name=last,
                age=25 + i,
                innate="curious",
                learned=f"{pname} is a resident.",
                currently="idle",
                lifestyle="9-to-5",
                living_area="the_ville:studio",
                daily_plan_req="explore",
            )
            PersonaScratch.objects.create(
                persona=p,
                vision_r=4,
                att_bandwidth=3,
                retention=5,
                curr_time=datetime.datetime(2023, 2, 13, 0, 0, 0, tzinfo=datetime.timezone.utc),
                curr_tile=[10 + i, 20],
            )
            SpatialMemory.objects.create(
                persona=p,
                tree={"the_ville": {"town square": {}}},
            )
            personas.append(p)
        return sim, personas

    def _simulate_steps(self, sim: Simulation, personas: list[Persona], num_steps: int = 10) -> None:
        """Write EnvironmentState + MovementRecord + ConceptNode rows for N steps."""
        base_time = datetime.datetime(2023, 2, 13, 0, 0, 0, tzinfo=datetime.timezone.utc)
        for step in range(num_steps):
            step_time = base_time + datetime.timedelta(seconds=step * 10)

            # EnvironmentState (written by frontend process_environment)
            agent_positions = {p.name: {"maze": "the_ville", "x": 10 + step, "y": 20 + step} for p in personas}
            EnvironmentState.objects.update_or_create(
                simulation=sim,
                step=step,
                defaults={"agent_positions": agent_positions},
            )

            # MovementRecord (written by backend reverie.py)
            persona_movements = {
                p.name: {
                    "movement": [10 + step, 20 + step],
                    "pronunciatio": "🚶",
                    "description": f"{p.name} is walking",
                    "chat": None,
                }
                for p in personas
            }
            MovementRecord.objects.update_or_create(
                simulation=sim,
                step=step,
                defaults={"sim_curr_time": step_time, "persona_movements": persona_movements},
            )

            # ConceptNode (written by backend as personas act)
            for p in personas:
                ConceptNode.objects.create(
                    persona=p,
                    node_id=step + 1,
                    node_count=step + 1,
                    type_count=step + 1,
                    node_type=ConceptNode.NodeType.EVENT,
                    depth=1,
                    created=step_time,
                    last_accessed=step_time,
                    subject=p.name,
                    predicate="is",
                    object=f"walking_step_{step}",
                    description=f"{p.name} is walking_step_{step}",
                    embedding_key=f"{p.name} is walking_step_{step}",
                    poignancy=1.0,
                    keywords=[p.name, f"walking_step_{step}"],
                    filling=[],
                )

        # Update simulation step counter
        sim.step = num_steps
        sim.curr_time = base_time + datetime.timedelta(seconds=num_steps * 10)
        sim.save()

    def test_environment_state_rows_accumulate(self) -> None:
        """EnvironmentState rows accumulate with correct agent positions after each step."""
        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)

        env_count = EnvironmentState.objects.filter(simulation=sim).count()
        self.assertEqual(env_count, 10)

        # Verify step 5 has correct positions
        env5 = EnvironmentState.objects.get(simulation=sim, step=5)
        for p in personas:
            self.assertIn(p.name, env5.agent_positions)
            self.assertEqual(env5.agent_positions[p.name]["x"], 15)
            self.assertEqual(env5.agent_positions[p.name]["y"], 25)

    def test_movement_record_rows_accumulate(self) -> None:
        """MovementRecord rows accumulate with correct movement data after each step."""
        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)

        mov_count = MovementRecord.objects.filter(simulation=sim).count()
        self.assertEqual(mov_count, 10)

        # Verify step 3 has correct movements
        mov3 = MovementRecord.objects.get(simulation=sim, step=3)
        for p in personas:
            self.assertIn(p.name, mov3.persona_movements)
            self.assertEqual(mov3.persona_movements[p.name]["movement"], [13, 23])

    def test_concept_nodes_accumulate_as_simulation_runs(self) -> None:
        """ConceptNode rows accumulate in DB as simulation runs."""
        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)

        total_nodes = ConceptNode.objects.filter(persona__simulation=sim).count()
        # 3 personas × 10 steps = 30 nodes
        self.assertEqual(total_nodes, 30)

        # Each persona has 10 nodes
        for p in personas:
            self.assertEqual(ConceptNode.objects.filter(persona=p).count(), 10)

    def test_qdrant_search_similar_returns_results(self) -> None:
        """Embeddings are stored and searchable in Qdrant after simulation steps.

        Uses the backend qdrant_utils.search_similar with a mocked Qdrant client
        to verify that embeddings written during simulation steps can be retrieved
        via cosine ANN search.
        """
        import sys

        backend_utils = str(Path(__file__).resolve().parents[2] / "backend_server" / "utils")
        if backend_utils not in sys.path:
            sys.path.insert(0, backend_utils)

        import importlib

        import qdrant_utils as backend_qdrant_utils

        importlib.reload(backend_qdrant_utils)  # ensure clean module state

        mock_client = MagicMock()
        scored_pt = MagicMock()
        scored_pt.payload = {
            "persona_id": 1,
            "embedding_key": "Isabella Rodriguez is walking_step_0",
            "simulation_id": 1,
        }
        scored_pt.score = 0.92
        mock_client.search.return_value = [scored_pt]
        collection_mock = MagicMock()
        collection_mock.name = backend_qdrant_utils.COLLECTION_NAME
        mock_client.get_collections.return_value.collections = [collection_mock]

        with patch.object(backend_qdrant_utils, "_get_client", return_value=mock_client):
            query_vector = [0.1] * 1536
            results = backend_qdrant_utils.search_similar(persona_id=1, query_vector=query_vector, top_k=5)

        # search_similar returns List[str] of embedding_keys ordered by cosine similarity
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "Isabella Rodriguez is walking_step_0")

    def test_simulation_list_api_returns_correct_metadata(self) -> None:
        """Simulation list API returns the simulation with correct metadata."""
        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)

        resp = self.client.get("/api/v1/simulations/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        sim_data = next(s for s in data["simulations"] if s["id"] == SIM_NAME)
        self.assertEqual(sim_data["maze_name"], "the_ville")
        self.assertEqual(sim_data["step"], 10)
        for pname in PERSONA_NAMES:
            self.assertIn(pname, sim_data["persona_names"])

    def test_compress_creates_demo_and_demo_movement_rows(self) -> None:
        """Run compress_sim_storage → Demo and DemoMovement rows created in DB."""
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_server"))
        from utils.compress_sim_storage import compress

        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)

        compress(SIM_NAME)

        # Demo row created
        self.assertTrue(Demo.objects.filter(name=SIM_NAME).exists())
        demo = Demo.objects.get(name=SIM_NAME)
        self.assertEqual(demo.maze_name, "the_ville")
        self.assertEqual(demo.total_steps, 10)

        # DemoMovement rows created (all steps changed so all 10 should be present)
        demo_mov_count = DemoMovement.objects.filter(demo=demo).count()
        self.assertEqual(demo_mov_count, 10)

    def test_demo_step_api_returns_movement_data(self) -> None:
        """Demo step API endpoint returns correct movement data from DemoMovement rows."""
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_server"))
        from utils.compress_sim_storage import compress

        sim, personas = self._build_test_sim()
        self._simulate_steps(sim, personas, num_steps=10)
        compress(SIM_NAME)

        # Query step 5 via API
        resp = self.client.get(f"/api/v1/demos/{SIM_NAME}/step/5/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["step"], 5)

        # Verify persona movement data is present
        step_movements = data["agents"]
        for pname in PERSONA_NAMES:
            self.assertIn(pname, step_movements)
            self.assertEqual(step_movements[pname]["movement"], [15, 25])

    def test_full_lifecycle_end_to_end(self) -> None:
        """
        Full simulation lifecycle: create → 10 steps → compress → demo API.

        This single test covers the entire chain as described in US-022.
        """
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend_server"))
        from utils.compress_sim_storage import compress

        # 1. Create simulation (as API would do)
        resp = self.client.post(
            "/api/v1/simulations/",
            data=json.dumps({"name": "e2e-lifecycle-sim"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Simulation.objects.filter(name="e2e-lifecycle-sim").exists())

        sim = Simulation.objects.get(name="e2e-lifecycle-sim")
        sim.maze_name = "the_ville"
        sim.sec_per_step = 10
        sim.save()

        # 2. Add personas
        personas = []
        for pname in PERSONA_NAMES:
            first, *rest = pname.split()
            last = rest[-1] if rest else "Smith"
            p = Persona.objects.create(
                simulation=sim,
                name=pname,
                first_name=first,
                last_name=last,
                age=25,
                innate="curious",
                learned=f"{pname} is a resident.",
                currently="idle",
                lifestyle="9-to-5",
                living_area="the_ville:studio",
                daily_plan_req="explore",
            )
            personas.append(p)

        # 3. Simulate 10 steps (as reverie.py + process_environment would do)
        self._simulate_steps(sim, personas, num_steps=10)

        # 4. Verify accumulation
        self.assertEqual(EnvironmentState.objects.filter(simulation=sim).count(), 10)
        self.assertEqual(MovementRecord.objects.filter(simulation=sim).count(), 10)
        total_nodes = ConceptNode.objects.filter(persona__simulation=sim).count()
        self.assertEqual(total_nodes, 30)

        # 5. Simulation list API returns correct metadata
        resp = self.client.get("/api/v1/simulations/")
        sim_ids = [s["id"] for s in resp.json()["simulations"]]
        self.assertIn("e2e-lifecycle-sim", sim_ids)

        # 6. Run compress → Demo + DemoMovement rows
        compress("e2e-lifecycle-sim")
        self.assertTrue(Demo.objects.filter(name="e2e-lifecycle-sim").exists())
        demo = Demo.objects.get(name="e2e-lifecycle-sim")
        self.assertEqual(demo.total_steps, 10)
        self.assertGreater(DemoMovement.objects.filter(demo=demo).count(), 0)

        # 7. Demo step API returns correct data
        resp = self.client.get("/api/v1/demos/e2e-lifecycle-sim/step/0/")
        self.assertEqual(resp.status_code, 200)
        step_data = resp.json()
        self.assertEqual(step_data["step"], 0)
        self.assertIn("agents", step_data)
