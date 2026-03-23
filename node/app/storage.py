import json
import os
import threading
from typing import Dict, List

from .config import DATA_DIR, CHECKPOINT_FILE, WAL_FILE
from .models import CounterUpdate, ClusterCRDTState

_storage_lock = threading.RLock()


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

    with _storage_lock:
        with open(WAL_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())


def load_checkpoint() -> ClusterCRDTState:
    ensure_storage()
    with _storage_lock:
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

    with _storage_lock:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_file, CHECKPOINT_FILE)


def load_wal_updates() -> List[CounterUpdate]:
    ensure_storage()
    updates: List[CounterUpdate] = []

    with _storage_lock:
        with open(WAL_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                rec = json.loads(line)
                if rec.get("kind") == "counter_update":
                    updates.append(
                        CounterUpdate(
                            poll_id=rec["poll_id"],
                            option=rec["option"],
                            node_id=rec["node_id"],
                            value=rec["value"],
                        )
                    )

    return updates


def truncate_wal() -> None:
    ensure_storage()
    with _storage_lock:
        with open(WAL_FILE, "w", encoding="utf-8") as f:
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())