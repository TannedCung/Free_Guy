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
from typing import Any, Optional, Union


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

    def __init__(self, f_saved: str) -> None:
        self.id_to_node = dict()

        self.seq_event = []
        self.seq_thought = []
        self.seq_chat = []

        self.kw_to_event = dict()
        self.kw_to_thought = dict()
        self.kw_to_chat = dict()

        self.kw_strength_event = dict()
        self.kw_strength_thought = dict()

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

    def save(self, out_json: str) -> None:
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

        # Adding in the kw_strength
        if f"{p} {o}" != "is idle":
            for kw in kw_list:
                if kw in self.kw_strength_event:
                    self.kw_strength_event[kw] += 1
                else:
                    self.kw_strength_event[kw] = 1

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

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

        # Adding in the kw_strength
        if f"{p} {o}" != "is idle":
            for kw in kw_list:
                if kw in self.kw_strength_thought:
                    self.kw_strength_thought[kw] += 1
                else:
                    self.kw_strength_thought[kw] = 1

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

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

        self.embeddings[embedding_pair[0]] = embedding_pair[1]

        return node

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
