import json
import logging
import os
import threading
from typing import List

from pydantic import ValidationError

from .config import DATA_DIR, CHECKPOINT_FILE, WAL_FILE
from .models import CounterUpdate, ClusterCRDTState
from .locks import storage_lock

logger = logging.getLogger(__name__)



def ensure_storage() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            json.dump({"polls": {}}, f)

    if not os.path.exists(WAL_FILE):
        open(WAL_FILE, "a", encoding="utf-8").close()


def append_wal_update(upd: CounterUpdate) -> None:
    """
    Write-ahead log append.
    One JSON record per line.
    """
    ensure_storage()
    record = {
        "kind": "counter_update",
        "poll_id": upd.poll_id,
        "option": upd.option,
        "node_id": upd.node_id,
        "value": upd.value,
    }

    line = json.dumps(record, ensure_ascii=False)

    with storage_lock:
        with open(WAL_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())


def load_checkpoint() -> ClusterCRDTState:
    ensure_storage()
    with storage_lock:
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    return ClusterCRDTState(**data)


def write_checkpoint(state: ClusterCRDTState) -> None:
    """
    Atomic checkpoint write:
    write tmp -> fsync -> replace
    """
    ensure_storage()
    tmp_file = CHECKPOINT_FILE + ".tmp"
    payload = state.model_dump()

    with storage_lock:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_file, CHECKPOINT_FILE)


def load_wal_updates() -> List[CounterUpdate]:
    ensure_storage()
    updates: List[CounterUpdate] = []
    skipped = 0

    with storage_lock:
        with open(WAL_FILE, "r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as e:
                    skipped += 1
                    logger.warning(
                        "Skipping corrupted WAL line %d: invalid JSON (%s)",
                        line_no,
                        e,
                    )
                    continue

                if rec.get("kind") != "counter_update":
                    skipped += 1
                    logger.warning(
                        "Skipping WAL line %d: unsupported kind=%r",
                        line_no,
                        rec.get("kind"),
                    )
                    continue

                try:
                    upd = CounterUpdate.model_validate(
                        {
                            "poll_id": rec.get("poll_id"),
                            "option": rec.get("option"),
                            "node_id": rec.get("node_id"),
                            "value": rec.get("value"),
                        }
                    )
                except ValidationError as e:
                    skipped += 1
                    logger.warning(
                        "Skipping invalid WAL line %d: %s",
                        line_no,
                        e.errors(),
                    )
                    continue

                updates.append(upd)

    logger.info(
        "WAL recovery completed: recovered=%d skipped=%d",
        len(updates),
        skipped,
    )
    return updates


def truncate_wal() -> None:
    ensure_storage()
    with storage_lock:
        with open(WAL_FILE, "w", encoding="utf-8") as f:
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())