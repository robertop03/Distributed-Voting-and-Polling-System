from typing import Dict, List
import threading

from .config import NODE_ID
from .models import CounterUpdate, PollCRDTState, ClusterCRDTState

# g_counter[poll_id][option][node_id] = int
g_counter: Dict[str, Dict[str, Dict[str, int]]] = {}
_state_lock = threading.RLock()


def list_polls() -> List[str]:
    with _state_lock:
        return list(g_counter.keys())


def ensure_poll(poll_id: str) -> None:
    if poll_id not in g_counter:
        g_counter[poll_id] = {}


def ensure_option(poll_id: str, option: str) -> None:
    ensure_poll(poll_id)
    if option not in g_counter[poll_id]:
        g_counter[poll_id][option] = {}


def build_local_increment_update(poll_id: str, option: str) -> CounterUpdate:
    """
    Compute the next local CRDT increment without applying it yet.
    This is useful for WAL-before-apply.
    """
    with _state_lock:
        ensure_option(poll_id, option)
        current = g_counter[poll_id][option].get(NODE_ID, 0) + 1
        return CounterUpdate(
            poll_id=poll_id,
            option=option,
            node_id=NODE_ID,
            value=current,
        )


def would_change_update(upd: CounterUpdate) -> bool:
    with _state_lock:
        ensure_option(upd.poll_id, upd.option)
        prev = g_counter[upd.poll_id][upd.option].get(upd.node_id, 0)
        return upd.value > prev


def apply_update(upd: CounterUpdate) -> bool:
    """
    Apply one CRDT component update with max-merge semantics.
    Returns True iff the in-memory state changed.
    """
    with _state_lock:
        ensure_option(upd.poll_id, upd.option)
        prev = g_counter[upd.poll_id][upd.option].get(upd.node_id, 0)
        newv = max(prev, upd.value)
        changed = newv != prev
        g_counter[upd.poll_id][upd.option][upd.node_id] = newv
        return changed


def export_poll_state(poll_id: str) -> PollCRDTState:
    with _state_lock:
        ensure_poll(poll_id)
        counts = {opt: dict(nodes) for opt, nodes in g_counter[poll_id].items()}
        return PollCRDTState(counts=counts)


def export_cluster_state() -> ClusterCRDTState:
    with _state_lock:
        polls: Dict[str, PollCRDTState] = {}
        for poll_id, poll_data in g_counter.items():
            counts = {opt: dict(nodes) for opt, nodes in poll_data.items()}
            polls[poll_id] = PollCRDTState(counts=counts)
        return ClusterCRDTState(polls=polls)


def query_poll_counts(poll_id: str) -> Dict[str, int]:
    with _state_lock:
        ensure_poll(poll_id)
        result: Dict[str, int] = {}
        for opt, nodes in g_counter[poll_id].items():
            result[opt] = sum(nodes.values())
        return result


def replace_cluster_state(other: ClusterCRDTState) -> None:
    """
    Replace in-memory state with a recovered snapshot.
    Used only during startup recovery.
    """
    global g_counter
    with _state_lock:
        new_state: Dict[str, Dict[str, Dict[str, int]]] = {}
        for poll_id, poll_state in other.polls.items():
            new_state[poll_id] = {}
            for opt, nodes in poll_state.counts.items():
                new_state[poll_id][opt] = dict(nodes)
        g_counter = new_state


def extract_new_updates_from_poll_state(
    poll_id: str,
    other: PollCRDTState,
) -> List[CounterUpdate]:
    """
    Compare a remote poll state with local state and return only the updates
    that would increase at least one local component.
    """
    updates: List[CounterUpdate] = []

    with _state_lock:
        ensure_poll(poll_id)
        for opt, nodes in other.counts.items():
            ensure_option(poll_id, opt)
            for node_id, value in nodes.items():
                prev = g_counter[poll_id][opt].get(node_id, 0)
                if value > prev:
                    updates.append(
                        CounterUpdate(
                            poll_id=poll_id,
                            option=opt,
                            node_id=node_id,
                            value=value,
                        )
                    )

    return updates


def extract_new_updates_from_cluster_state(
    other: ClusterCRDTState,
) -> List[CounterUpdate]:
    """
    Compare a full remote cluster state with local state and return only the
    component updates that are actually newer than local state.
    """
    updates: List[CounterUpdate] = []

    with _state_lock:
        for poll_id, poll_state in other.polls.items():
            ensure_poll(poll_id)
            for opt, nodes in poll_state.counts.items():
                ensure_option(poll_id, opt)
                for node_id, value in nodes.items():
                    prev = g_counter[poll_id][opt].get(node_id, 0)
                    if value > prev:
                        updates.append(
                            CounterUpdate(
                                poll_id=poll_id,
                                option=opt,
                                node_id=node_id,
                                value=value,
                            )
                        )

    return updates