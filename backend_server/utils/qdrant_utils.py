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
# For Qdrant Cloud: set QDRANT_URL (e.g. https://xyz.qdrant.io) and QDRANT_API_KEY.
# For self-hosted: set QDRANT_HOST and QDRANT_PORT (defaults: localhost:6333).
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
EMBEDDING_DIMENSION = int(os.environ.get("EMBEDDING_DIMENSION", "1536"))
COLLECTION_NAME = "persona_embeddings"

# ── Module-level singleton ─────────────────────────────────────────────────────
_client: Optional[QdrantClient] = None


def _get_client() -> QdrantClient:
    """Return (and lazily create) the module-level Qdrant client singleton.

    Uses QDRANT_URL + QDRANT_API_KEY for Qdrant Cloud, or QDRANT_HOST + QDRANT_PORT
    for a self-hosted instance.
    """
    global _client
    if _client is None:
        if QDRANT_URL:
            _client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
        else:
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


# ── Public API ─────────────────────────────────────────────────────────────────


def store_embedding(
    persona_id: int,
    simulation_id: int,
    embedding_key: str,
    vector: List[float],
) -> None:
    """Upsert a single embedding point into the persona_embeddings collection.

    Args:
        persona_id: Primary key of the Persona DB row.
        simulation_id: Primary key of the Simulation DB row.
        embedding_key: A stable string key that identifies this embedding
                       (e.g. the concept node's embedding_key field).
        vector: The embedding vector (length must match EMBEDDING_DIMENSION).
    """
    _ensure_collection()
    client = _get_client()

    # Use a deterministic UUID derived from (persona_id, embedding_key) so
    # repeated upserts with the same key overwrite the same point.
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{persona_id}:{embedding_key}"))

    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "persona_id": persona_id,
                    "simulation_id": simulation_id,
                    "embedding_key": embedding_key,
                },
            )
        ],
    )


def get_embedding(persona_id: int, embedding_key: str) -> Optional[List[float]]:
    """Retrieve a single vector from Qdrant by payload filter.

    Args:
        persona_id: Primary key of the Persona DB row.
        embedding_key: The string key that identifies the embedding.

    Returns:
        The vector as a list of floats, or None if not found.
    """
    _ensure_collection()
    client = _get_client()

    results, _ = client.scroll(
        collection_name=COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="persona_id",
                    match=models.MatchValue(value=persona_id),
                ),
                models.FieldCondition(
                    key="embedding_key",
                    match=models.MatchValue(value=embedding_key),
                ),
            ]
        ),
        with_vectors=True,
        limit=1,
    )

    if results and results[0].vector is not None:
        vec = results[0].vector
        if isinstance(vec, list):
            return vec  # type: ignore[return-value]
    return None


def search_similar(
    persona_id: int,
    query_vector: List[float],
    top_k: int = 20,
) -> List[str]:
    """Return top-k embedding_keys nearest to *query_vector* using cosine ANN.

    Results are filtered to *persona_id* so cross-persona leakage is prevented.

    Args:
        persona_id: Primary key of the Persona DB row.
        query_vector: The query embedding vector.
        top_k: Maximum number of results to return.

    Returns:
        Ordered list of embedding_key strings (closest first).
    """
    _ensure_collection()
    client = _get_client()

    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        query_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="persona_id",
                    match=models.MatchValue(value=persona_id),
                )
            ]
        ),
        limit=top_k,
        with_payload=True,
    )

    return [hit.payload["embedding_key"] for hit in hits if hit.payload]


def delete_persona_embeddings(persona_id: int) -> None:
    """Remove ALL embedding points for a given persona.

    Args:
        persona_id: Primary key of the Persona DB row.
    """
    _ensure_collection()
    client = _get_client()

    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="persona_id",
                        match=models.MatchValue(value=persona_id),
                    )
                ]
            )
        ),
    )


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
