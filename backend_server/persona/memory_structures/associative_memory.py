"""
Author: Joon Sung Park (joonspk@stanford.edu)

File: associative_memory.py
Description: Defines the core long-term memory module for generative agents.

Note (May 1, 2023) -- this class is the Memory Stream module in the generative
agents paper.
"""

from __future__ import annotations

import datetime
import json
import logging
from typing import Any, List, Optional, Union

logger = logging.getLogger(__name__)


class ConceptNode:
    node_id: str
    node_count: int
    type_count: int
    type: str
    depth: int

    created: datetime.datetime
    expiration: Optional[datetime.datetime]
    last_accessed: datetime.datetime

    subject: str
    predicate: str
    object: str

    description: str
    embedding_key: str
    poignancy: float
    keywords: set[str]
    filling: list[Any]

    def __init__(
        self,
        node_id: str,
        node_count: int,
        type_count: int,
        node_type: str,
        depth: int,
        created: datetime.datetime,
        expiration: Optional[datetime.datetime],
        s: str,
        p: str,
        o: str,
        description: str,
        embedding_key: str,
        poignancy: float,
        keywords: set[str],
        filling: list[Any],
    ) -> None:
        self.node_id = node_id
        self.node_count = node_count
        self.type_count = type_count
        self.type = node_type  # thought / event / chat
        self.depth = depth

        self.created = created
        self.expiration = expiration
        self.last_accessed = self.created

        self.subject = s
        self.predicate = p
        self.object = o

        self.description = description
        self.embedding_key = embedding_key
        self.poignancy = poignancy
        self.keywords = keywords
        self.filling = filling

    def spo_summary(self) -> tuple[str, str, str]:
        return (self.subject, self.predicate, self.object)


class AssociativeMemory:
    id_to_node: dict[str, ConceptNode]

    seq_event: list[ConceptNode]
    seq_thought: list[ConceptNode]
    seq_chat: list[ConceptNode]

    kw_to_event: dict[str, list[ConceptNode]]
    kw_to_thought: dict[str, list[ConceptNode]]
    kw_to_chat: dict[str, list[ConceptNode]]

    kw_strength_event: dict[str, int]
    kw_strength_thought: dict[str, int]

    embeddings: dict[str, list[float]]

    def __init__(self, f_saved: Optional[str] = None, persona_id: Optional[int] = None) -> None:
        self._persona_id: Optional[int] = persona_id
        self._simulation_id: Optional[int] = None
        # Suppress DB/Qdrant writes during init loading phase
        self._loading: bool = True

        self.id_to_node = dict()

        self.seq_event = []
        self.seq_thought = []
        self.seq_chat = []

        self.kw_to_event = dict()
        self.kw_to_thought = dict()
        self.kw_to_chat = dict()

        self.kw_strength_event = dict()
        self.kw_strength_thought = dict()

        self.embeddings = dict()
        # Cache: embedding_key -> ConceptNode (for Qdrant-based similarity retrieval)
        self._embedding_key_to_node: dict[str, ConceptNode] = dict()

        if persona_id is not None:
            self._load_from_db(persona_id)
        elif f_saved is not None:
            self._load_from_files(f_saved)

        self._loading = False

    # ── File-based loading (legacy) ────────────────────────────────────────────

    def _load_from_files(self, f_saved: str) -> None:
        self.embeddings = json.load(open(f_saved + "/embeddings.json"))

        nodes_load = json.load(open(f_saved + "/nodes.json"))
        for count in range(len(nodes_load.keys())):
            node_id = f"node_{str(count + 1)}"
            node_details = nodes_load[node_id]

            _node_count = node_details["node_count"]
            _type_count = node_details["type_count"]
            node_type = node_details["type"]
            _depth = node_details["depth"]

            created = datetime.datetime.strptime(node_details["created"], "%Y-%m-%d %H:%M:%S")
            expiration = None
            if node_details["expiration"]:
                expiration = datetime.datetime.strptime(node_details["expiration"], "%Y-%m-%d %H:%M:%S")

            s = node_details["subject"]
            p = node_details["predicate"]
            o = node_details["object"]

            description = node_details["description"]
            embedding_pair: tuple[str, list[float]] = (
                node_details["embedding_key"],
                self.embeddings[node_details["embedding_key"]],
            )
            poignancy = node_details["poignancy"]
            keywords = set(node_details["keywords"])
            filling = node_details["filling"]

            if node_type == "event":
                self.add_event(created, expiration, s, p, o, description, keywords, poignancy, embedding_pair, filling)
            elif node_type == "chat":
                self.add_chat(created, expiration, s, p, o, description, keywords, poignancy, embedding_pair, filling)
            elif node_type == "thought":
                self.add_thought(
                    created, expiration, s, p, o, description, keywords, poignancy, embedding_pair, filling
                )

        kw_strength_load = json.load(open(f_saved + "/kw_strength.json"))
        if kw_strength_load["kw_strength_event"]:
            self.kw_strength_event = kw_strength_load["kw_strength_event"]
        if kw_strength_load["kw_strength_thought"]:
            self.kw_strength_thought = kw_strength_load["kw_strength_thought"]

    # ── DB-based loading ───────────────────────────────────────────────────────

    def _load_from_db(self, persona_id: int) -> None:
        """Load all ConceptNodes, KeywordStrengths, and embeddings from DB/Qdrant."""
        try:
            from translator.models import ConceptNode as ConceptNodeModel
            from translator.models import KeywordStrength as KeywordStrengthModel
            from translator.models import Persona as PersonaModel
        except Exception as exc:
            logger.warning("Could not import translator models for DB load: %s", exc)
            return

        # Resolve simulation_id for Qdrant operations
        try:
            persona_row = PersonaModel.objects.select_related("simulation").get(pk=persona_id)
            self._simulation_id = persona_row.simulation_id
        except Exception as exc:
            logger.warning("Could not load Persona(pk=%s): %s", persona_id, exc)

        # Load embeddings from Qdrant into in-memory dict
        self._load_embeddings_from_qdrant(persona_id)

        # Load concept nodes ordered by node_count so id_to_node is populated correctly
        nodes_qs = ConceptNodeModel.objects.filter(persona_id=persona_id).order_by("node_count")
        for row in nodes_qs:
            created: datetime.datetime = (
                row.created.replace(tzinfo=None)
                if row.created and row.created.tzinfo
                else (row.created or datetime.datetime.now())
            )
            expiration: Optional[datetime.datetime] = None
            if row.expiration:
                expiration = row.expiration.replace(tzinfo=None) if row.expiration.tzinfo else row.expiration

            embedding_key = row.embedding_key or ""
            vector = self.embeddings.get(embedding_key, [])
            embedding_pair: tuple[str, list[float]] = (embedding_key, vector)

            keywords = set(row.keywords) if row.keywords else set()
            filling = row.filling if row.filling else []

            if row.node_type == "event":
                self.add_event(
                    created,
                    expiration,
                    row.subject,
                    row.predicate,
                    row.object,
                    row.description,
                    keywords,
                    row.poignancy,
                    embedding_pair,
                    filling,
                )
            elif row.node_type == "chat":
                self.add_chat(
                    created,
                    expiration,
                    row.subject,
                    row.predicate,
                    row.object,
                    row.description,
                    keywords,
                    row.poignancy,
                    embedding_pair,
                    filling,
                )
            elif row.node_type == "thought":
                self.add_thought(
                    created,
                    expiration,
                    row.subject,
                    row.predicate,
                    row.object,
                    row.description,
                    keywords,
                    row.poignancy,
                    embedding_pair,
                    filling,
                )

        # Load keyword strengths from DB (override in-memory values built by add_*)
        for ks in KeywordStrengthModel.objects.filter(persona_id=persona_id):
            if ks.strength_type == "event":
                self.kw_strength_event[ks.keyword] = ks.strength
            elif ks.strength_type == "thought":
                self.kw_strength_thought[ks.keyword] = ks.strength

    def _load_embeddings_from_qdrant(self, persona_id: int) -> None:
        """Scroll all embeddings for persona_id from Qdrant into self.embeddings."""
        try:
            from qdrant_client.http import models as qdrant_models

            from utils import qdrant_utils

            qdrant_utils._ensure_collection()
            client = qdrant_utils._get_client()

            offset = None
            while True:
                results, next_offset = client.scroll(
                    collection_name=qdrant_utils.COLLECTION_NAME,
                    scroll_filter=qdrant_models.Filter(
                        must=[
                            qdrant_models.FieldCondition(
                                key="persona_id",
                                match=qdrant_models.MatchValue(value=persona_id),
                            )
                        ]
                    ),
                    with_vectors=True,
                    limit=500,
                    offset=offset,
                )
                for point in results:
                    if point.vector is not None and isinstance(point.vector, list) and point.payload:
                        emb_key = point.payload.get("embedding_key", "")
                        if emb_key:
                            self.embeddings[emb_key] = point.vector  # type: ignore[assignment]
                if next_offset is None:
                    break
                offset = next_offset
        except Exception as exc:
            logger.warning("Could not load embeddings from Qdrant for persona %s: %s", persona_id, exc)

    # ── DB persistence helpers ─────────────────────────────────────────────────

    def _save_node_to_db(self, node: ConceptNode) -> None:
        """Upsert a ConceptNode row immediately on creation (DB mode only)."""
        if self._persona_id is None:
            return
        try:
            from django.utils import timezone
            from translator.models import ConceptNode as ConceptNodeModel

            # node_id string is "node_N"; DB column stores int N
            node_id_int = int(node.node_id.replace("node_", ""))

            created_aware = timezone.make_aware(node.created) if node.created.tzinfo is None else node.created
            expiration_aware: Optional[datetime.datetime] = None
            if node.expiration:
                expiration_aware = (
                    timezone.make_aware(node.expiration) if node.expiration.tzinfo is None else node.expiration
                )
            last_accessed_aware = (
                timezone.make_aware(node.last_accessed) if node.last_accessed.tzinfo is None else node.last_accessed
            )

            ConceptNodeModel.objects.update_or_create(
                persona_id=self._persona_id,
                node_id=node_id_int,
                defaults=dict(
                    node_count=node.node_count,
                    type_count=node.type_count,
                    node_type=node.type,
                    depth=node.depth,
                    created=created_aware,
                    expiration=expiration_aware,
                    last_accessed=last_accessed_aware,
                    subject=node.subject,
                    predicate=node.predicate,
                    object=node.object,
                    description=node.description,
                    embedding_key=node.embedding_key,
                    poignancy=node.poignancy,
                    keywords=list(node.keywords),
                    filling=node.filling,
                ),
            )
        except Exception as exc:
            logger.warning("Could not save ConceptNode to DB: %s", exc)

    def _store_embedding_in_qdrant(self, embedding_key: str, vector: List[float]) -> None:
        """Store a single embedding in Qdrant (DB mode only)."""
        if self._persona_id is None or self._simulation_id is None:
            return
        try:
            from utils.qdrant_utils import store_embedding

            store_embedding(self._persona_id, self._simulation_id, embedding_key, vector)
        except Exception as exc:
            logger.warning("Could not store embedding in Qdrant: %s", exc)

    def _update_keyword_strength_in_db(
        self,
        keywords: set[str],
        predicate: str,
        object_str: str,
        strength_type: str,
    ) -> None:
        """Atomically increment KeywordStrength rows using F() expressions."""
        if self._persona_id is None:
            return
        if f"{predicate} {object_str}" == "is idle":
            return
        try:
            from django.db import transaction
            from django.db.models import F
            from translator.models import KeywordStrength as KeywordStrengthModel

            kw_list = [kw.lower() for kw in keywords]
            for kw in kw_list:
                with transaction.atomic():
                    obj, created = KeywordStrengthModel.objects.get_or_create(
                        persona_id=self._persona_id,
                        keyword=kw,
                        strength_type=strength_type,
                        defaults={"strength": 1},
                    )
                    if not created:
                        KeywordStrengthModel.objects.filter(pk=obj.pk).update(strength=F("strength") + 1)
        except Exception as exc:
            logger.warning("Could not update KeywordStrength in DB: %s", exc)

    # ── Save ──────────────────────────────────────────────────────────────────

    def save(self, out_json: Optional[str] = None) -> None:
        """Save memory to files (legacy) or no-op when in DB mode (incremental saves).

        In DB mode, ConceptNodes and embeddings are saved immediately in add_*,
        and keyword strengths are updated atomically there too. No bulk save needed.
        """
        if out_json is None:
            # DB mode — nothing to do (incremental saves already happened)
            return

        # Legacy file-based save
        r: dict[str, Any] = dict()
        for count in range(len(self.id_to_node.keys()), 0, -1):
            node_id = f"node_{str(count)}"
            node = self.id_to_node[node_id]

            r[node_id] = dict()
            r[node_id]["node_count"] = node.node_count
            r[node_id]["type_count"] = node.type_count
            r[node_id]["type"] = node.type
            r[node_id]["depth"] = node.depth

            r[node_id]["created"] = node.created.strftime("%Y-%m-%d %H:%M:%S")
            r[node_id]["expiration"] = None
            if node.expiration:
                r[node_id]["expiration"] = node.expiration.strftime("%Y-%m-%d %H:%M:%S")

            r[node_id]["subject"] = node.subject
            r[node_id]["predicate"] = node.predicate
            r[node_id]["object"] = node.object

            r[node_id]["description"] = node.description
            r[node_id]["embedding_key"] = node.embedding_key
            r[node_id]["poignancy"] = node.poignancy
            r[node_id]["keywords"] = list(node.keywords)
            r[node_id]["filling"] = node.filling

        with open(out_json + "/nodes.json", "w") as outfile:
            json.dump(r, outfile)

        r2: dict[str, Any] = dict()
        r2["kw_strength_event"] = self.kw_strength_event
        r2["kw_strength_thought"] = self.kw_strength_thought
        with open(out_json + "/kw_strength.json", "w") as outfile:
            json.dump(r2, outfile)

        with open(out_json + "/embeddings.json", "w") as outfile:
            json.dump(self.embeddings, outfile)

    # ── Node creation ─────────────────────────────────────────────────────────

    def add_event(
        self,
        created: datetime.datetime,
        expiration: Optional[datetime.datetime],
        s: str,
        p: str,
        o: str,
        description: str,
        keywords: set[str],
        poignancy: float,
        embedding_pair: tuple[str, list[float]],
        filling: list[Any],
    ) -> ConceptNode:
        # Setting up the node ID and counts.
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_event) + 1
        node_type = "event"
        node_id = f"node_{str(node_count)}"
        depth = 0

        # Node type specific clean up.
        if "(" in description:
            description = " ".join(description.split()[:3]) + " " + description.split("(")[-1][:-1]

        # Creating the <ConceptNode> object.
        node = ConceptNode(
            node_id,
            node_count,
            type_count,
            node_type,
            depth,
            created,
            expiration,
            s,
            p,
            o,
            description,
            embedding_pair[0],
            poignancy,
            keywords,
            filling,
        )

        # Creating various dictionary cache for fast access.
        self.seq_event[0:0] = [node]
        kw_list = [i.lower() for i in keywords]
        for kw in kw_list:
            if kw in self.kw_to_event:
                self.kw_to_event[kw][0:0] = [node]
            else:
                self.kw_to_event[kw] = [node]
        self.id_to_node[node_id] = node
        self._embedding_key_to_node[embedding_pair[0]] = node

        # Adding in the kw_strength (in-memory)
        if f"{p} {o}" != "is idle":
            for kw in kw_list:
                if kw in self.kw_strength_event:
                    self.kw_strength_event[kw] += 1
                else:
                    self.kw_strength_event[kw] = 1

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        # Persist to DB / Qdrant (skipped during init loading)
        if not self._loading:
            self._save_node_to_db(node)
            if embedding_pair[1]:
                self._store_embedding_in_qdrant(embedding_pair[0], embedding_pair[1])
            self._update_keyword_strength_in_db(keywords, p, o, "event")

        return node

    def add_thought(
        self,
        created: datetime.datetime,
        expiration: Optional[datetime.datetime],
        s: str,
        p: str,
        o: str,
        description: str,
        keywords: set[str],
        poignancy: float,
        embedding_pair: tuple[str, list[float]],
        filling: list[Any],
    ) -> ConceptNode:
        # Setting up the node ID and counts.
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_thought) + 1
        node_type = "thought"
        node_id = f"node_{str(node_count)}"
        depth = 1
        try:
            if filling:
                depth += max([self.id_to_node[i].depth for i in filling])
        except (KeyError, ValueError):
            pass

        # Creating the <ConceptNode> object.
        node = ConceptNode(
            node_id,
            node_count,
            type_count,
            node_type,
            depth,
            created,
            expiration,
            s,
            p,
            o,
            description,
            embedding_pair[0],
            poignancy,
            keywords,
            filling,
        )

        # Creating various dictionary cache for fast access.
        self.seq_thought[0:0] = [node]
        kw_list = [i.lower() for i in keywords]
        for kw in kw_list:
            if kw in self.kw_to_thought:
                self.kw_to_thought[kw][0:0] = [node]
            else:
                self.kw_to_thought[kw] = [node]
        self.id_to_node[node_id] = node
        self._embedding_key_to_node[embedding_pair[0]] = node

        # Adding in the kw_strength (in-memory)
        if f"{p} {o}" != "is idle":
            for kw in kw_list:
                if kw in self.kw_strength_thought:
                    self.kw_strength_thought[kw] += 1
                else:
                    self.kw_strength_thought[kw] = 1

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        # Persist to DB / Qdrant (skipped during init loading)
        if not self._loading:
            self._save_node_to_db(node)
            if embedding_pair[1]:
                self._store_embedding_in_qdrant(embedding_pair[0], embedding_pair[1])
            self._update_keyword_strength_in_db(keywords, p, o, "thought")

        return node

    def add_chat(
        self,
        created: datetime.datetime,
        expiration: Optional[datetime.datetime],
        s: str,
        p: str,
        o: str,
        description: str,
        keywords: set[str],
        poignancy: float,
        embedding_pair: tuple[str, list[float]],
        filling: list[Any],
    ) -> ConceptNode:
        # Setting up the node ID and counts.
        node_count = len(self.id_to_node.keys()) + 1
        type_count = len(self.seq_chat) + 1
        node_type = "chat"
        node_id = f"node_{str(node_count)}"
        depth = 0

        # Creating the <ConceptNode> object.
        node = ConceptNode(
            node_id,
            node_count,
            type_count,
            node_type,
            depth,
            created,
            expiration,
            s,
            p,
            o,
            description,
            embedding_pair[0],
            poignancy,
            keywords,
            filling,
        )

        # Creating various dictionary cache for fast access.
        self.seq_chat[0:0] = [node]
        kw_list = [i.lower() for i in keywords]
        for kw in kw_list:
            if kw in self.kw_to_chat:
                self.kw_to_chat[kw][0:0] = [node]
            else:
                self.kw_to_chat[kw] = [node]
        self.id_to_node[node_id] = node
        self._embedding_key_to_node[embedding_pair[0]] = node

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        # Persist to DB / Qdrant (skipped during init loading)
        if not self._loading:
            self._save_node_to_db(node)
            if embedding_pair[1]:
                self._store_embedding_in_qdrant(embedding_pair[0], embedding_pair[1])

        return node

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_summarized_latest_events(self, retention: int) -> set[tuple[str, str, str]]:
        ret_set: set[tuple[str, str, str]] = set()
        for e_node in self.seq_event[:retention]:
            ret_set.add(e_node.spo_summary())
        return ret_set

    def get_str_seq_events(self) -> str:
        ret_str = ""
        for count, event in enumerate(self.seq_event):
            ret_str += f"{'Event', len(self.seq_event) - count, ': ', event.spo_summary(), ' -- ', event.description}\n"
        return ret_str

    def get_str_seq_thoughts(self) -> str:
        ret_str = ""
        for count, event in enumerate(self.seq_thought):
            ret_str += (
                f"{'Thought', len(self.seq_thought) - count, ': ', event.spo_summary(), ' -- ', event.description}"
            )
        return ret_str

    def get_str_seq_chats(self) -> str:
        ret_str = ""
        for count, event in enumerate(self.seq_chat):
            ret_str += f"with {event.object.content} ({event.description})\n"  # type: ignore[attr-defined]
            ret_str += f"{event.created.strftime('%B %d, %Y, %H:%M:%S')}\n"
            for row in event.filling:
                ret_str += f"{row[0]}: {row[1]}\n"
        return ret_str

    def retrieve_relevant_thoughts(self, s_content: str, p_content: str, o_content: str) -> set[ConceptNode]:
        contents = [s_content, p_content, o_content]

        ret: list[ConceptNode] = []
        for i in contents:
            if i in self.kw_to_thought:
                ret += self.kw_to_thought[i.lower()]

        return set(ret)

    def retrieve_relevant_events(self, s_content: str, p_content: str, o_content: str) -> set[ConceptNode]:
        contents = [s_content, p_content, o_content]

        ret: list[ConceptNode] = []
        for i in contents:
            if i in self.kw_to_event:
                ret += self.kw_to_event[i]

        return set(ret)

    def get_last_chat(self, target_persona_name: str) -> Union[ConceptNode, bool]:
        if target_persona_name.lower() in self.kw_to_chat:
            return self.kw_to_chat[target_persona_name.lower()][0]
        else:
            return False

    def retrieve_similar_nodes(self, query_vector: List[float], top_k: int = 20) -> list[ConceptNode]:
        """Return up to top_k ConceptNodes whose embeddings are most similar to query_vector.

        Uses Qdrant ANN search (cosine) then resolves results via in-memory cache.
        Falls back to an empty list if Qdrant is unavailable or DB mode not active.
        """
        if self._persona_id is None:
            return []
        try:
            from utils.qdrant_utils import search_similar

            embedding_keys = search_similar(self._persona_id, query_vector, top_k)
            nodes: list[ConceptNode] = []
            for key in embedding_keys:
                node = self._embedding_key_to_node.get(key)
                if node is not None:
                    nodes.append(node)
            return nodes
        except Exception as exc:
            logger.warning("retrieve_similar_nodes failed: %s", exc)
            return []
