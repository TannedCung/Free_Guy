"""Qdrant utility module for embedding storage and retrieval.

All embedding operations go through this single interface.
The Qdrant client is a module-level singleton to avoid reconnecting per call.
"""

import os
import uuid
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models

# ── Configuration ──────────────────────────────────────────────────────────────
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
COLLECTION_NAME = "persona_embeddings"

# ── Module-level singleton ─────────────────────────────────────────────────────
_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    """Return (and lazily create) the module-level Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    return _client


def _ensure_collection() -> None:
    """Create *persona_embeddings* collection if it does not already exist."""
    client = _get_client()
    existing = {col.name for col in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=models.Distance.COSINE,
            ),
        )


def batch_store_embeddings(
    persona_id: int,
    simulation_id: int,
    embeddings: dict,
    batch_size: int = 500,
) -> int:
    """Batch-upsert a dict of {embedding_key: vector} into Qdrant.

    Args:
        persona_id: Primary key of the Persona DB row.
        simulation_id: Primary key of the Simulation DB row.
        embeddings: Mapping from embedding_key string to float vector list.
        batch_size: Number of points to upsert per API call.

    Returns:
        Total number of points upserted.
    """
    _ensure_collection()
    client = _get_client()

    items = [(k, v) for k, v in embeddings.items() if isinstance(v, list) and v]
    total = 0
    for i in range(0, len(items), batch_size):
        chunk = items[i : i + batch_size]
        points: List[models.PointStruct] = [
            models.PointStruct(
                id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{persona_id}:{key}")),
                vector=vector,
                payload={
                    "persona_id": persona_id,
                    "simulation_id": simulation_id,
                    "embedding_key": key,
                },
            )
            for key, vector in chunk
        ]
        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total += len(points)
    return total


def copy_persona_embeddings(
    src_persona_id: int,
    dst_persona_id: int,
    dst_simulation_id: int,
) -> None:
    """Deep-copy all embedding vectors from one persona to another.

    Used during simulation fork operations so the new persona starts with
    identical embeddings without re-computing them.

    Args:
        src_persona_id: Primary key of the source Persona row.
        dst_persona_id: Primary key of the destination Persona row.
        dst_simulation_id: Primary key of the destination Simulation row.
    """
    _ensure_collection()
    client = _get_client()

    offset = None
    while True:
        results, next_offset = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="persona_id",
                        match=models.MatchValue(value=src_persona_id),
                    )
                ]
            ),
            with_vectors=True,
            limit=100,
            offset=offset,
        )

        if not results:
            break

        new_points: List[models.PointStruct] = []
        for point in results:
            if point.payload is None or point.vector is None:
                continue
            embedding_key: str = point.payload["embedding_key"]
            vector = point.vector
            new_point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{dst_persona_id}:{embedding_key}"))
            new_points.append(
                models.PointStruct(
                    id=new_point_id,
                    vector=vector,
                    payload={
                        "persona_id": dst_persona_id,
                        "simulation_id": dst_simulation_id,
                        "embedding_key": embedding_key,
                    },
                )
            )

        if new_points:
            client.upsert(collection_name=COLLECTION_NAME, points=new_points)

        if next_offset is None:
            break
        offset = next_offset
