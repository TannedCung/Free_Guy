"""
Database utility helpers for reading and writing RuntimeState rows.

These functions provide a simple key/value IPC mechanism backed by the
RuntimeState table (frontend_server/translator/models.py) to replace
the previous temp-file-based approach.

Usage (from any non-Django process that has already called init_django()):
    from utils.db_utils import get_runtime_state, set_runtime_state
    set_runtime_state("curr_sim_code", {"sim_code": "my_sim"})
    val = get_runtime_state("curr_sim_code")
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def set_runtime_state(key: str, value: Any) -> None:
    """
    Upsert a RuntimeState row with the given key and value.

    VALUE is stored as-is in the JSONB column; it must be JSON-serialisable.
    Silently no-ops if Django is unavailable.
    """
    try:
        from translator.models import RuntimeState

        RuntimeState.objects.update_or_create(
            key=key,
            defaults={"value": value},
        )
        logger.debug("db_utils: set_runtime_state key=%s", key)
    except Exception as exc:
        logger.error("db_utils: set_runtime_state failed for key=%s: %s", key, exc, exc_info=True)


def get_runtime_state(key: str, default: Optional[Any] = None) -> Any:
    """
    Retrieve the value for *key* from the RuntimeState table.

    Returns *default* if the row does not exist or Django is unavailable.
    """
    try:
        from translator.models import RuntimeState

        obj = RuntimeState.objects.filter(key=key).first()
        if obj is None:
            return default
        return obj.value
    except Exception as exc:
        logger.error("db_utils: get_runtime_state failed for key=%s: %s", key, exc, exc_info=True)
        return default
