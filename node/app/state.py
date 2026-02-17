# in-memory state + helpers
from typing import Dict
from .config import NODE_ID
from .models import CounterUpdate, PollCRDTState

# G-Counter state:
# g_counter[poll_id][option][node_id] = non-negative int
g_counter: Dict[str, Dict[str, Dict[str, int]]] = {}


def ensure_poll(poll_id: str) -> None:
    if poll_id not in g_counter:
        g_counter[poll_id] = {}


def ensure_option(poll_id: str, option: str) -> None:
    ensure_poll(poll_id)
    if option not in g_counter[poll_id]:
        g_counter[poll_id][option] = {}


def local_increment(poll_id: str, option: str) -> CounterUpdate:
    """
    Increment local component of the G-Counter and return an idempotent update.
    """
    ensure_option(poll_id, option)
    current = g_counter[poll_id][option].get(NODE_ID, 0) + 1
    g_counter[poll_id][option][NODE_ID] = current
    return CounterUpdate(poll_id=poll_id, option=option, node_id=NODE_ID, value=current)


def merge_update(upd: CounterUpdate) -> bool:
    """
    Merge one component update using max().
    Returns True if it changed local state, False otherwise.
    """
    ensure_option(upd.poll_id, upd.option)
    prev = g_counter[upd.poll_id][upd.option].get(upd.node_id, 0)
    newv = max(prev, upd.value)
    changed = newv != prev
    g_counter[upd.poll_id][upd.option][upd.node_id] = newv
    return changed


def export_poll_state(poll_id: str) -> PollCRDTState:
    """
    Return full CRDT state for a poll (for sync/merge).
    """
    ensure_poll(poll_id)
    # deep-copy-ish (avoid exposing internal dicts directly)
    counts = {opt: dict(nodes) for opt, nodes in g_counter[poll_id].items()}
    return PollCRDTState(counts=counts)


def merge_poll_state(poll_id: str, other: PollCRDTState) -> None:
    """
    Merge full state: component-wise max for each option/node_id.
    """
    ensure_poll(poll_id)
    for opt, nodes in other.counts.items():
        ensure_option(poll_id, opt)
        for node_id, value in nodes.items():
            prev = g_counter[poll_id][opt].get(node_id, 0)
            g_counter[poll_id][opt][node_id] = max(prev, value)


def query_poll_counts(poll_id: str) -> Dict[str, int]:
    """
    Aggregated counts per option (sum over node components).
    """
    ensure_poll(poll_id)
    result: Dict[str, int] = {}
    for opt, nodes in g_counter[poll_id].items():
        result[opt] = sum(nodes.values())
    return result
